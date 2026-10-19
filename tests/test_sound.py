"""Audio library, eligibility, ducking and preview sound wiring. Unit tests use fake commands."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
sys.path.insert(0, str(PROJECT_ROOT / "tests"))
import analyze
import audio_library
import common
import ingest
import production
import review
import sound
from test_ingest import TRIP
from test_production import production_config
from test_review import FakeReview, candidates

EBUR_SUMMARY = "Summary:\n\n  Integrated loudness:\n    I:         -18.2 LUFS\n\n  True peak:\n    Peak:       -3.1 dBFS\n"


def fake_measure(command, **_kwargs):
    if command[0] == "ffprobe":
        return subprocess.CompletedProcess(command, 0, json.dumps({"streams": [{"codec_type": "audio", "sample_rate": "48000",
                                                                                "channels": 2}], "format": {"duration": "12.5"}}), "")
    return subprocess.CompletedProcess(command, 0, "", EBUR_SUMMARY)


def empty_library(root):
    """Tests start from an empty audio library, never the user's registered files."""
    common.write_json(root / "config/media-licenses.json", {"schema_version": 2, "assets": []})


def fields(asset_id="sfx-boing", kind="sfx", **extra):
    base = {"id": asset_id, "kind": kind, "file": f"assets/audio/user/{asset_id}.wav", "title": "Boing", "source": "user library",
            "license": "CC0", "license_status": "verified", "license_evidence": "https://example.invalid/license",
            "claim_status": "documented_low_risk", "claim_evidence": "provider states not registered with Content ID",
            "allowed_platforms": ["youtube"], "moods": ["silly"]}
    return base | extra


class DuckingTests(unittest.TestCase):
    def test_envelope_ducks_under_speech_and_stays_valid(self):
        for duration, speech in [(300, [[60, 120]]), (300, [[0, 40]]), (300, []), (20, [[5, 10]]),
                                 (300, [[100, 130], [140, 170]]), (300, [[280, 320]]), (2, [])]:
            with self.subTest(duration=duration, speech=speech):
                points = sound.duck_envelope(duration, speech)
                production._gain(points, duration)
        points = dict(map(tuple, sound.duck_envelope(300, [[60, 120]])))
        self.assertEqual((points[0], points[15], points[60], points[120], points[126], points[299]), (-60, -16, -28, -28, -16, -60))
        merged = dict(map(tuple, sound.duck_envelope(300, [[100, 130], [140, 170]])))
        self.assertNotIn(130, merged)
        with self.assertRaises(ValueError):
            sound.duck_envelope(1, [])

    def test_speech_maps_through_cuts_and_speed(self):
        segments = [{"start": 15, "end": 18}, {"start": 29, "end": 31}, {"start": 40, "end": 41}]
        self.assertEqual(sound.map_speech([[12, 20], [30, 36]], 1.0, segments), [[90, 180], [240, 270]])
        self.assertEqual(sound.map_speech([[12, 20]], 2.0, segments), [[45, 90]])

    def test_sfx_density_and_repetition_warnings(self):
        calm = [{"asset": "sfx-a", "from": 0}, {"asset": "sfx-b", "from": 300}]
        self.assertEqual(sound.sfx_warnings(calm), [])
        busy = [{"asset": f"sfx-{i}", "from": i * 100} for i in range(10)]
        self.assertIn("within one minute", sound.sfx_warnings(busy)[0])
        self.assertIn("repeats", sound.sfx_warnings([{"asset": "sfx-a", "from": 0}, {"asset": "sfx-a", "from": 60}])[0])


class LibraryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="vlog-audio-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        (self.root / "config").mkdir()
        (self.root / "assets/audio/user").mkdir(parents=True)
        empty_library(self.root)
        for name in ["sfx-boing", "bgm-walk", "sfx-pending"]:
            (self.root / f"assets/audio/user/{name}.wav").write_text(f"audio {name}")
        for module in (common, production):
            root_patch = patch.object(module, "ROOT", self.root)
            root_patch.start()
            self.addCleanup(root_patch.stop)

    def register(self, **values):
        with patch.object(audio_library, "run_command", side_effect=fake_measure):
            return audio_library.register(values)

    def test_register_measures_and_records_evidence(self):
        entry = self.register(**fields())
        self.assertEqual((entry["duration_seconds"], entry["integrated_lufs"], entry["true_peak_dbtp"]), (12.5, -18.2, -3.1))
        self.assertEqual(entry["platform_check"], "not_checked")
        report = audio_library.check(self.root)
        self.assertEqual(report[0]["usable"], True)
        with self.assertRaisesRegex(ValueError, "already registered"):
            self.register(**fields())

    def test_bad_entries_are_rejected(self):
        for values in [fields(asset_id="boing"), fields(kind="bgm"), fields(file="sources/trip/a.wav"),
                       fields(file="assets/audio/user/missing.wav"), fields(moods=["sad-trombone"]),
                       fields(allowed_platforms=["vimeo"]), fields(title=" ")]:
            with self.subTest(values=values), self.assertRaises(ValueError):
                self.register(**values)

    def test_eligibility_is_narrowed_only_by_platform(self):
        ok = audio_library.validate_entry(fields() | {"free": True, "sha256": "x", "origin": "user"})
        self.assertTrue(audio_library.eligibility(ok, ["youtube"])[0])
        self.assertEqual(audio_library.eligibility(ok, ["youtube", "tiktok"]), (False, "platform_rights_incomplete"))
        for change, reason in [({"claim_status": "unknown"}, "claim_pending"), ({"claim_status": "known_claim"}, "known_claim_requirement"),
                               ({"requires_whitelist": True}, "known_claim_requirement"), ({"license_status": "pending"}, "license_pending"),
                               ({"license_evidence": None}, "license_pending"), ({"claim_evidence": ""}, "claim_pending"),
                               ({"free": False}, "not_free"), ({"attribution_required": True, "attribution_text": ""}, "attribution_text_missing")]:
            with self.subTest(change=change):
                self.assertEqual(audio_library.eligibility(ok | change, ["youtube"]), (False, reason))

    def test_check_detects_changed_files_and_credits_use_attribution(self):
        self.register(**fields(asset_id="bgm-walk", kind="bgm", file="assets/audio/user/bgm-walk.wav", title="Walk",
                               author="Composer", license="CC BY 4.0", attribution_text="Walk by Composer (CC BY 4.0)"))
        self.register(**fields())
        self.assertEqual(audio_library.credits(["bgm-walk", "sfx-boing"], self.root),
                         ["Walk by Composer (CC BY 4.0)", "Boing (user library, CC0)"])
        (self.root / "assets/audio/user/sfx-boing.wav").write_text("changed")
        with self.assertRaisesRegex(ValueError, "hash changed"):
            audio_library.check(self.root)

    def test_claude_found_audio_needs_production_download_flags(self):
        common.write_json(self.root / "config/project.json", json.loads((PROJECT_ROOT / "config/setup.example.json").read_text()))
        with self.assertRaises(ValueError):
            self.register(**fields(origin="claude_search"))
        (self.root / "sources/trip").mkdir(parents=True)
        config = production_config()
        common.write_json(self.root / "config/project.json", config, replace=True)
        with self.assertRaisesRegex(ValueError, "audio_search and audio_downloads"):
            self.register(**fields(origin="claude_search"))
        config.update(audio_search=True, audio_downloads=True)
        common.write_json(self.root / "config/project.json", config, replace=True)
        self.assertEqual(self.register(**fields(origin="claude_search"))["origin"], "claude_search")


class PreviewSoundTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="vlog-sound-review-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        trip = self.root / TRIP
        trip.mkdir(parents=True)
        for name in ["a-hlg.mov", "IMG_0001.HEIC"]:
            (trip / name).write_text(f"original {name}")
        (self.root / "config").mkdir()
        common.write_json(self.root / "config/project.json", production_config())
        empty_library(self.root)
        (self.root / "assets/audio/user").mkdir(parents=True)
        for module in (common, production):
            root_patch = patch.object(module, "ROOT", self.root)
            root_patch.start()
            self.addCleanup(root_patch.stop)
        for values in [fields(), fields(asset_id="bgm-walk", kind="bgm", file="assets/audio/user/bgm-walk.wav", moods=["bright"]),
                       fields(asset_id="sfx-pending", file="assets/audio/user/sfx-pending.wav", claim_status="unknown")]:
            (self.root / values["file"]).write_text(f"audio {values['id']}")
            with patch.object(audio_library, "run_command", side_effect=fake_measure):
                audio_library.register(values)
        self.media = FakeReview()
        with patch.object(ingest, "run_command", side_effect=self.media):
            self.run_id = ingest.ingest(TRIP)["run_id"]
        with patch.object(analyze, "run_command", side_effect=self.media):
            analyze.analyze(self.run_id)
        self.run = self.root / "work" / self.run_id

    def write_candidates(self, sfx_asset="sfx-boing"):
        data = candidates()
        first = data["candidates"][0]
        first.update(range=[0.0, 3.0], key_moment=1.0)
        first["plan"].update(cuts=[[0.0, 1.0], [1.5, 3.0]], captions=[], sfx=[{"name": "띠용", "at": 1.0, "asset": sfx_asset}],
                             bgm={"asset": "bgm-walk", "gain_db": -18, "note": "가볍게"})
        common.write_json(self.run / "candidates.json", data, replace=(self.run / "candidates.json").exists())

    def test_eligible_audio_is_staged_and_ducked(self):
        self.write_candidates()
        common.write_json(self.run / "analysis/v001/transcript.json", {"status": "done", "segments": [
            {"start": 0.5, "end": 1.4, "text": "여기 아까 왔던 데", "words": [], "suspect": []},
            {"start": 2.0, "end": 2.5, "text": "한글자막 by", "words": [], "suspect": ["known_phrase"]}]}, replace=True)
        with patch.object(review, "run_command", side_effect=self.media):
            review.build(self.run_id)
        self.assertEqual(sorted(p.name for p in (self.run / "audio").iterdir()), ["bgm-walk.wav", "sfx-boing.wav"])
        job = common.read_json(self.run / "review/v1/render-input.json")["jobs"][0]
        cues = {c["id"]: c for c in job["props"]["audio"]}
        self.assertEqual(cues["sfx-0"]["from"], 30)
        self.assertEqual(cues["bgm"]["duration"], job["props"]["durationInFrames"])
        speech_frames = [db for frame, db in cues["bgm"]["gain"] if 15 <= frame <= 42]
        self.assertIn(-30, speech_frames)
        page = (self.run / "review/v1/index.html").read_text(encoding="utf-8")
        self.assertIn("BGM bgm-walk -18 dB · 대사 중 -12 dB · 가볍게", page)

    def test_ineligible_audio_stops_before_rendering(self):
        self.write_candidates("sfx-pending")
        before = (self.run / "state.json").read_bytes()
        with patch.object(review, "run_command", side_effect=AssertionError("No rendering allowed")):
            with self.assertRaisesRegex(ValueError, "sfx-pending cannot be used yet: claim_pending"):
                review.build(self.run_id)
        self.assertEqual((self.run / "state.json").read_bytes(), before)

    def test_candidate_audio_fields_are_validated(self):
        entries = {"v001": {"id": "v001", "kind": "video", "original": "x.mp4", "duration_seconds": 60.0, "proxy": "p.mp4"},
                   "p001": {"id": "p001", "kind": "photo", "original": "y.jpg", "proxy": "q.jpg"}}
        for change in [lambda p: p["sfx"][0].update(asset="bgm-walk"), lambda p: p["sfx"][0].update(asset="boing"),
                       lambda p: p["sfx"][0].update(gain_db=6), lambda p: p.update(bgm={"asset": "sfx-boing"}),
                       lambda p: p.update(bgm={"asset": "bgm-walk", "gain_db": -2}), lambda p: p.update(bgm=3)]:
            data = candidates()
            data["candidates"][0]["plan"]["sfx"][0]["asset"] = "sfx-boing"
            change(data["candidates"][0]["plan"])
            with self.subTest(change=change), self.assertRaises(ValueError):
                review.validate_candidates(data, entries)


@unittest.skipUnless(os.environ.get("VLOG_MEDIA_TESTS") == "1", "set VLOG_MEDIA_TESTS=1 (scripts/smoke-media.sh)")
class SoundMediaTests(unittest.TestCase):
    """Registers generated tones and renders a preview whose BGM ducks under Korean TTS speech."""

    def setUp(self):
        keep = os.environ.get("VLOG_KEEP_REVIEW_DIR")
        self.root = Path(tempfile.mkdtemp(prefix="vlog-sound-media-", dir=keep)).resolve()
        if not keep:
            self.addCleanup(shutil.rmtree, self.root, True)
        trip = self.root / TRIP
        trip.mkdir(parents=True)
        (self.root / "config").mkdir()
        common.write_json(self.root / "config/project.json", production_config())
        empty_library(self.root)
        for name in [".tools", "renderer"]:
            (self.root / name).symlink_to(PROJECT_ROOT / name)
        for module in (common, production):
            root_patch = patch.object(module, "ROOT", self.root)
            root_patch.start()
            self.addCleanup(root_patch.stop)
        ffmpeg = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-n"]
        library = self.root / "assets/audio/user"
        library.mkdir(parents=True)
        common.run_command(ffmpeg + ["-f", "lavfi", "-i", "sine=frequency=262:duration=20", "-af", "volume=0.3",
                                     "-ar", "48000", "-ac", "2", str(library / "bgm-tone.wav")])
        common.run_command(ffmpeg + ["-f", "lavfi", "-i", "sine=frequency=1200:duration=0.4", "-ar", "48000",
                                     str(library / "sfx-blip.wav")])
        for values in [fields(asset_id="bgm-tone", kind="bgm", file="assets/audio/user/bgm-tone.wav", title="Tone", moods=["calm"]),
                       fields(asset_id="sfx-blip", file="assets/audio/user/sfx-blip.wav", title="Blip")]:
            audio_library.register(values)
        common.run_command(ffmpeg + ["-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=30:duration=6",
                                     "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", "6", "-c:v", "libx264",
                                     "-c:a", "aac", str(trip / "quiet.mp4")])

    def test_preview_contains_library_sound(self):
        run_id = ingest.ingest(TRIP)["run_id"]
        with patch.object(analyze, "model_path", return_value=None):
            analyze.analyze(run_id)
        run = self.root / "work" / run_id
        data = candidates()
        data["candidates"] = data["candidates"][:1]
        data["candidates"][0].update(source="v001", range=[0.5, 5.5], key_moment=2.0, preview=True)
        data["candidates"][0]["plan"].update(cuts=[[0.5, 5.5]], captions=[], sfx=[{"name": "삑", "at": 2.0, "asset": "sfx-blip"}],
                                             bgm={"asset": "bgm-tone", "gain_db": -16})
        common.write_json(run / "candidates.json", data)
        # Pretend people talk from 1.0s to 3.0s of the source (0.5s–2.5s after the cut) to observe ducking.
        common.write_json(run / "analysis/v001/transcript.json", {"status": "done", "segments": [
            {"start": 1.0, "end": 3.0, "text": "대사", "words": [], "suspect": []}]}, replace=True)
        review.build(run_id)
        clip = run / "review/v1/c01/preview.mp4"

        def bgm_level(start, end):
            stats = common.run_command(["ffmpeg", "-hide_banner", "-nostdin", "-i", str(clip), "-af",
                                        f"atrim={start}:{end},bandpass=f=262:w=40,astats=metadata=0", "-f", "null", "-"]).stderr
            return float(stats.split("Overall", 1)[1].split("RMS level dB:", 1)[1].split()[0])
        ducked, normal = bgm_level(0.9, 2.1), bgm_level(3.0, 4.2)
        self.assertGreater(normal - ducked, 8, (normal, ducked))
        self.assertLess(normal - ducked, 16, (normal, ducked))
        log = common.run_command(["ffmpeg", "-hide_banner", "-nostdin", "-i", str(clip), "-af", "ebur128", "-f", "null", "-"]).stderr
        integrated = float(log.rsplit("Summary:", 1)[1].split("I:", 1)[1].split("LUFS", 1)[0])
        self.assertGreater(integrated, -45, "library BGM/SFX should be audible over a silent source")
        print(json.dumps({"preview": str(clip), "integrated_lufs": integrated, "bgm_rms_db": {"speech": ducked, "no_speech": normal}}))


if __name__ == "__main__":
    unittest.main()

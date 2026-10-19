"""Assemble and long-form render contracts. Unit tests use fake commands; media tests need VLOG_MEDIA_TESTS=1."""
import json
import os
from pathlib import Path
import re
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
import assemble
import audio_library
import common
import ingest
import production
import render_prod
import review
from test_ingest import TRIP
from test_production import production_config
from test_review import FakeReview
from test_sound import fake_measure, fields


def plan_candidates():
    return {"candidates": [
        {"id": "c01", "title": "골목 헤매기", "tag": "fun", "source": "v001", "range": [0.0, 3.0], "key_moment": 1.0,
         "reason": "반복되는 골목", "plan": {"cuts": [[0.0, 1.0], [1.5, 3.0]], "zoom": 1.1,
         "captions": [{"kind": "variety", "text": "결국 원점", "at": 1.0, "duration": 1.0}],
         "sfx": [{"name": "띠용", "at": 1.0, "asset": "sfx-boing"}, {"name": "쿵", "at": 2.0}],
         "bgm": {"asset": "bgm-walk", "gain_db": -18}}},
        {"id": "c02", "title": "노을", "tag": "mood", "source": "p001", "key_moment": 1.0, "reason": "여운",
         "plan": {"photo_seconds": 3.0, "zoom": 1.05, "transition": "fade",
                  "captions": [{"kind": "mood", "text": "그래도 바람은 좋았다", "at": 0.5, "duration": 2.0}],
                  "bgm": {"asset": "bgm-walk", "gain_db": -18}}},
        {"id": "c03", "title": "빠진 장면", "tag": "fun", "source": "v002", "range": [0.0, 2.0], "key_moment": 0.5,
         "reason": "테스트", "plan": {"cuts": [[0.0, 2.0]]}}]}


class LongformFixture(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="vlog-longform-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        trip = self.root / TRIP
        trip.mkdir(parents=True)
        for name in ["a-hlg.mov", "b-vfr.mp4", "IMG_0001.HEIC"]:
            (trip / name).write_text(f"original {name}")
        (self.root / "config").mkdir()
        self.config = production_config()
        common.write_json(self.root / "config/project.json", self.config)
        shutil.copy2(PROJECT_ROOT / "config/media-licenses.json", self.root / "config/media-licenses.json")
        shutil.copytree(PROJECT_ROOT / "renderer/assets/fonts", self.root / "renderer/assets/fonts")
        shutil.copy2(PROJECT_ROOT / "config/fonts-lock.json", self.root / "config/fonts-lock.json")
        (self.root / "assets/audio/user").mkdir(parents=True)
        for module in (common, production):
            root_patch = patch.object(module, "ROOT", self.root)
            root_patch.start()
            self.addCleanup(root_patch.stop)
        for values in [fields(), fields(asset_id="bgm-walk", kind="bgm", file="assets/audio/user/bgm-walk.wav", moods=["bright"])]:
            (self.root / values["file"]).write_text(f"audio {values['id']}")
            with patch.object(audio_library, "run_command", side_effect=fake_measure):
                audio_library.register(values)
        self.media = FakeReview()
        with patch.object(ingest, "run_command", side_effect=self.media):
            self.run_id = ingest.ingest(TRIP)["run_id"]
        with patch.object(analyze, "run_command", side_effect=self.media):
            analyze.analyze(self.run_id)
        self.run = self.root / "work" / self.run_id
        common.write_json(self.run / "analysis/v001/transcript.json", {"status": "done", "segments": [
            {"start": 0.2, "end": 0.9, "text": "여기 아까", "words": [], "suspect": []}]}, replace=True)

    def review_and_select(self, decisions, order=None, candidates=None):
        common.write_json(self.run / "candidates.json", candidates or plan_candidates(),
                          replace=(self.run / "candidates.json").exists())
        with patch.object(review, "run_command", side_effect=self.media):
            review.build(self.run_id)
        selection = {"decisions": decisions} | ({"order": order} if order else {})
        common.write_json(self.run / "selection.json", selection, replace=(self.run / "selection.json").exists())
        return review.select(self.run_id)

    def config_with(self, **changes):
        config = production_config()
        config.update(changes)
        common.write_json(self.root / "config/project.json", config, replace=True)


ADOPT_TWO = {"c01": {"decision": "adopt"}, "c02": {"decision": "adopt"}, "c03": {"decision": "drop"}}


class AssembleTests(LongformFixture):
    def test_adopted_candidates_become_a_valid_timeline(self):
        self.review_and_select(ADOPT_TWO)
        state = assemble.assemble(self.run_id)
        self.assertEqual((state["stage"], state["status"], state["duration_seconds"]), ("assembled", "pending", 5.5))
        timeline = common.read_json(self.run / "timeline.json")
        # Shooting order: the photo (10:30Z) comes before the clip (12:00Z).
        self.assertEqual([c["id"] for c in timeline["clips"]], ["c02-k0", "c01-k0", "c01-k1"])
        self.assertEqual([(c["from"], c["duration"], c.get("in")) for c in timeline["clips"]], [(0, 90, None), (90, 30, 0), (120, 45, 45)])
        self.assertEqual(timeline["clips"][0]["transition"], "fade")
        cues = {c["id"]: c for c in timeline["audio"]}
        self.assertEqual(sorted(cues), ["bgm-0", "c01-o0", "c01-o1", "c01-s0"])
        self.assertEqual((cues["bgm-0"]["from"], cues["bgm-0"]["duration"]), (0, 165))
        self.assertIn(-30, [db for _, db in cues["bgm-0"]["gain_db"]])
        self.assertEqual([(c["id"], c["from"]) for c in timeline["captions"]], [("c02-t0", 15), ("c01-t0", 120)])
        self.assertEqual(timeline["captions"][1]["preset"], "pop")
        report = (self.run / "assemble-report.md").read_text(encoding="utf-8")
        self.assertIn("효과음 '쿵'에 음원이 없어", report)

    def test_order_and_reassembly_keep_the_previous_timeline(self):
        self.review_and_select(ADOPT_TWO, order=["c01", "c02"])
        assemble.assemble(self.run_id)
        timeline = common.read_json(self.run / "timeline.json")
        self.assertEqual(timeline["clips"][0]["id"], "c01-k0")
        self.assertEqual(len([c for c in timeline["audio"] if c["kind"] == "bgm"]), 1)
        assemble.assemble(self.run_id)
        self.assertEqual(len(list(self.run.glob("timeline.prev-*.json"))), 1)

    def test_caption_edits_and_changed_selection_block_assembly(self):
        self.review_and_select(ADOPT_TWO | {"c02": {"decision": "caption_edit", "note": "더 짧게"}})
        with self.assertRaisesRegex(ValueError, "Resolve caption edits first"):
            assemble.assemble(self.run_id)
        self.review_and_select(ADOPT_TWO)
        common.write_json(self.run / "selection.json", {"decisions": ADOPT_TWO, "order": ["c02", "c01"]}, replace=True)
        with self.assertRaisesRegex(ValueError, "changed after selection"):
            assemble.assemble(self.run_id)

    def test_bad_order_rejected(self):
        self.review_and_select(ADOPT_TWO, order=["c01"])
        with self.assertRaisesRegex(ValueError, "every kept candidate"):
            assemble.assemble(self.run_id)


class FakeRender(FakeReview):
    """Stands in for render-prod.mjs and the final ffmpeg steps."""

    def __init__(self, frames, fail_node=False):
        super().__init__()
        self.frames, self.fail_node = frames, fail_node

    def __call__(self, command, **kwargs):
        tool, joined = Path(command[0]).name, " ".join(command)
        if tool == "node" and command[1].endswith("render-prod.mjs"):
            self.calls.append(command)
            folder = Path(command[4]) / "render" / f"v{command[3]}"
            if self.fail_node:
                raise RuntimeError("node exited 1: fake chunk failure")
            plan = common.read_json(folder / "render-plan.json")
            chunks = {}
            for chunk in plan["chunks"]:
                (folder / "chunks" / f"{chunk['id']}.mp4").write_text("chunk")
                chunks[chunk["id"]] = {"sha256": common.digest(folder / "chunks" / f"{chunk['id']}.mp4")}
            common.write_json(folder / "chunks.json", {"props_sha256": plan["props_sha256"], "chunks": chunks})
            (folder / "mix.wav").write_text("mix")
            return subprocess.CompletedProcess(command, 0, '{"status":"chunks_and_mix_ready"}', "")
        if tool == "ffmpeg" and "loudnorm" in joined and "measured_I" not in joined:
            values = {"input_i": "-14.2", "input_tp": "-1.6", "input_lra": "5.0", "input_thresh": "-24.0", "target_offset": "0.1"}
            return subprocess.CompletedProcess(command, 0, "", json.dumps(values))
        if tool == "ffmpeg" and ("concat" in command or "measured_I" in joined):
            Path(command[-1]).write_text("video")
            return subprocess.CompletedProcess(command, 0, "", "")
        if tool == "ffmpeg" and "-xerror" in command:
            return subprocess.CompletedProcess(command, 0, "", "")
        if tool == "ffprobe" and "-count_packets" in command:
            probe = {"streams": [{"codec_type": "video", "codec_name": "h264", "width": 1920, "height": 1080, "r_frame_rate": "30/1",
                                  "nb_read_packets": str(self.frames), "duration": str(self.frames / 30)},
                                 {"codec_type": "audio", "duration": str(self.frames / 30)}], "format": {"duration": str(self.frames / 30)}}
            return subprocess.CompletedProcess(command, 0, json.dumps(probe), "")
        return super().__call__(command, **kwargs)


class RenderTests(LongformFixture):
    def setUp(self):
        super().setUp()
        self.review_and_select(ADOPT_TWO)
        assemble.assemble(self.run_id)

    def render(self, media):
        with patch.object(render_prod, "run_command", side_effect=media):
            return render_prod.render(self.run_id)

    def test_render_is_refused_until_enabled(self):
        with self.assertRaisesRegex(ValueError, "production_render"):
            self.render(AssertionError("No commands"))

    def test_render_qa_records_outputs_and_reuse(self):
        self.config_with(production_render=True, production_profile=self.config["production_profile"] | {"chunk_seconds": 30})
        state = self.render(FakeRender(165))
        self.assertEqual((state["stage"], state["status"], state["render_version"]), ("rendered", "succeeded", 1))
        folder = self.run / "render/v1"
        verify = common.read_json(folder / "verify.json")
        self.assertTrue(all(verify["checks"].values()))
        self.assertEqual(verify["human_review"], "NOT_RUN")
        credits = (folder / "credits.md").read_text(encoding="utf-8")
        self.assertIn("Boing (user library, CC0)", credits)
        self.assertIn("Black Han Sans", credits)
        self.assertEqual(self.render(AssertionError("Unchanged inputs must not render again"))["render_version"], 1)

    def test_failed_render_resumes_the_same_version_and_qa_catches_frame_loss(self):
        self.config_with(production_render=True)
        with self.assertRaises(RuntimeError):
            self.render(FakeRender(165, fail_node=True))
        state = common.read_json(self.run / "state.json")
        self.assertEqual((state["stage"], state["status"]), ("render", "failed"))
        with self.assertRaisesRegex(ValueError, "Render QA failed: frames"):
            self.render(FakeRender(160))
        self.assertEqual(sorted(p.name for p in (self.run / "render").iterdir()), ["v1"])
        self.assertFalse((self.run / "render/v1/final.mp4").exists())

    def test_check_validates_without_rendering(self):
        with patch.object(render_prod, "run_command", side_effect=AssertionError("No rendering")):
            result = render_prod.check(self.run_id)
        self.assertEqual((result["status"], result["duration_seconds"]), ("PASS", 5.5))
        timeline = common.read_json(self.run / "timeline.json")
        timeline["captions"][0]["preset"] = "pop"
        common.write_json(self.run / "timeline.json", timeline, replace=True)
        with self.assertRaisesRegex(ValueError, "preset"):
            render_prod.check(self.run_id)

    def test_rendered_run_can_be_reviewed_again(self):
        self.config_with(production_render=True)
        self.render(FakeRender(165))
        with patch.object(review, "run_command", side_effect=self.media):
            self.assertEqual(review.build(self.run_id)["review_version"], 2)

    def test_timeout_grows_with_length(self):
        profile = {"timeout_seconds": 3600}
        self.assertEqual(render_prod.node_timeout(profile, 30 * 60), 3600)
        self.assertEqual(render_prod.node_timeout(profile, 30 * 60 * 20), 20 * 60 * 6 + 600)

    def test_chunk_plan_covers_every_frame(self):
        chunks = render_prod.chunk_plan(5401, 60)
        self.assertEqual([(c["start"], c["end"]) for c in chunks], [(0, 1800), (1800, 3600), (3600, 5400), (5400, 5401)])
        for bad in [10, 1000, "60"]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                config = production_config()
                config["production_profile"]["chunk_seconds"] = bad
                production.validate_production_config(config)


@unittest.skipUnless(os.environ.get("VLOG_MEDIA_TESTS") == "1", "set VLOG_MEDIA_TESTS=1 (scripts/smoke-media.sh)")
class LongformMediaTests(unittest.TestCase):
    """A 2-minute synthetic edit rendered in 30-second chunks; flash/beep pairs every 10 s measure A/V sync."""

    def setUp(self):
        keep = os.environ.get("VLOG_KEEP_REVIEW_DIR")
        self.root = Path(tempfile.mkdtemp(prefix="vlog-longform-media-", dir=keep)).resolve()
        if not keep:
            self.addCleanup(shutil.rmtree, self.root, True)
        trip = self.root / TRIP
        trip.mkdir(parents=True)
        (self.root / "config").mkdir()
        config = production_config()
        config.update(production_render=True)
        config["production_profile"] |= {"chunk_seconds": 30}
        common.write_json(self.root / "config/project.json", config)
        shutil.copy2(PROJECT_ROOT / "config/media-licenses.json", self.root / "config/media-licenses.json")
        shutil.copy2(PROJECT_ROOT / "config/fonts-lock.json", self.root / "config/fonts-lock.json")
        for name in [".tools", "renderer"]:
            (self.root / name).symlink_to(PROJECT_ROOT / name)
        for module in (common, production):
            root_patch = patch.object(module, "ROOT", self.root)
            root_patch.start()
            self.addCleanup(root_patch.stop)
        ffmpeg = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-n"]
        common.run_command(ffmpeg + [
            "-f", "lavfi", "-i", "color=c=black:s=1280x720:r=30:d=130",
            "-f", "lavfi", "-i", "sine=frequency=1000:duration=130,volume='if(lt(mod(t,10),0.2),1,0)':eval=frame",
            "-vf", "drawbox=x=0:y=0:w=iw:h=ih:color=white:t=fill:enable='lt(mod(t,10),0.2)'",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(trip / "flash.mp4")])
        png = self.root / "sunset.png"
        common.run_command(ffmpeg + ["-f", "lavfi", "-i", "gradients=s=1200x800:c0=0xff8a3d:c1=0x2b3a67:d=1",
                                     "-frames:v", "1", str(png)])
        common.run_command(["sips", "-s", "format", "heic", str(png), "--out", str(trip / "IMG_0001.HEIC")])
        library = self.root / "assets/audio/user"
        library.mkdir(parents=True)
        common.run_command(ffmpeg + ["-f", "lavfi", "-i", "sine=frequency=262:duration=180", "-af", "volume=0.3",
                                     "-ar", "48000", "-ac", "2", str(library / "bgm-tone.wav")])
        audio_library.register(fields(asset_id="bgm-tone", kind="bgm", file="assets/audio/user/bgm-tone.wav", title="Tone", moods=["calm"]))

    def onsets(self, path, audio):
        if audio:
            log = common.run_command(["ffmpeg", "-hide_banner", "-nostdin", "-i", str(path), "-vn", "-af",
                                      "bandpass=f=1000:w=100,silencedetect=noise=-40dB:d=0.5", "-f", "null", "-"]).stderr
            # silencedetect also reports a silence_end at end of file; keep only real beeps inside the video.
            duration = float(json.loads(common.run_command(["ffprobe", "-v", "error", "-show_format", "-of", "json", str(path)]).stdout)["format"]["duration"])
            return [float(t) for t in re.findall(r"silence_end: ([\d.]+)", log) if float(t) < duration - 0.5]
        log = common.run_command(["ffmpeg", "-hide_banner", "-nostdin", "-i", str(path), "-an", "-vf",
                                  "scale=64:36,signalstats,metadata=print:key=lavfi.signalstats.YAVG", "-f", "null", "-"]).stderr
        values = [(float(t), float(y)) for t, y in re.findall(r"pts_time:([\d.]+).*?\n.*?YAVG=([\d.]+)", log)]
        return [t for (t, y), (_, previous) in zip(values[1:], values) if y > 128 >= previous]

    def test_two_minute_render_is_complete_and_in_sync(self):
        run_id = ingest.ingest(TRIP)["run_id"]
        with patch.object(analyze, "model_path", return_value=None):
            analyze.analyze(run_id)
        run = self.root / "work" / run_id
        data = {"candidates": [
            {"id": "c01", "title": "긴 산책", "tag": "fun", "source": "v001", "range": [0.0, 125.0], "key_moment": 5.0,
             "reason": "합성 롱폼", "preview": False,
             "plan": {"cuts": [[0.0, 60.0], [65.0, 125.0]], "captions": [
                 {"kind": "situation", "text": "2분 합성 테스트", "at": 1.0, "duration": 4.0, "position": "upper_left"},
                 {"kind": "variety", "text": "아직도 걷는 중", "at": 70.0, "duration": 2.0}],
                 "bgm": {"asset": "bgm-tone", "gain_db": -24}}},
            {"id": "c02", "title": "노을", "tag": "mood", "source": "p001", "key_moment": 1.0, "reason": "여운",
             "plan": {"photo_seconds": 4.0, "transition": "fade",
                      "captions": [{"kind": "mood", "text": "그래도 바람은 좋았다", "at": 0.5, "duration": 3.0}]}}]}
        common.write_json(run / "candidates.json", data)
        review.build(run_id)
        common.write_json(run / "selection.json", {"decisions": {"c01": {"decision": "adopt"}, "c02": {"decision": "adopt"}}})
        review.select(run_id)
        assemble.assemble(run_id)
        state = render_prod.render(run_id)
        final = Path(state["final"])
        verify = common.read_json(final.parent / "verify.json")
        self.assertEqual(verify["frames"], 3720)
        self.assertGreaterEqual(verify["chunks"], 5)
        beeps, flashes = self.onsets(final, True), self.onsets(final, False)
        self.assertGreaterEqual(len(beeps), 10, beeps)
        offsets = [min(abs(b - f) for f in flashes) for b in beeps]
        self.assertLessEqual(max(offsets), 0.06, list(zip(beeps, offsets)))
        print(json.dumps({"final": str(final), "frames": verify["frames"], "chunks": verify["chunks"],
                          "elapsed_seconds": verify["elapsed_seconds"], "lufs": verify["integrated_lufs"],
                          "true_peak": verify["true_peak_dbtp"], "max_av_offset_s": round(max(offsets), 3)}))


if __name__ == "__main__":
    unittest.main()

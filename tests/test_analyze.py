"""Analyze contracts. Unit tests use fake commands; media tests run only with VLOG_MEDIA_TESTS=1."""
import array
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
sys.path.insert(0, str(PROJECT_ROOT / "tests"))
import analyze
import common
import ingest
import production
from test_ingest import TRIP, FakeMedia
from test_production import ORIGINALS, production_config

LOUD_LOG = "\n".join(
    f"[Parsed_ebur128_0 @ 0x1] t: {t / 10:.6f}   TARGET:-23 LUFS    M: {m} S:-30.0     I: -30.0 LUFS       LRA:   0.0 LU"
    for t, m in enumerate([-40.0] * 20 + [-18.0] * 6 + [-40.0] * 30 + [-17.0] * 4 + [-40.0] * 20))
SILENCE_LOG = ("[silencedetect @ 0x1] silence_start: 0\n[silencedetect @ 0x1] silence_end: 1.2 | silence_duration: 1.2\n"
               "[silencedetect @ 0x1] silence_start: 6.5\n[silencedetect @ 0x1] silence_end: 9.5 | silence_duration: 3.0\n")
SCENE_LOG = "[scdet @ 0x1] lavfi.scd.score: 21.651, lavfi.scd.time: 4\n"
WHISPER = {"transcription": [
    {"offsets": {"from": 500, "to": 1900}, "text": " 여기 아까 왔던 데 아니야?",
     "tokens": [{"text": "[_BEG_]", "offsets": {"from": 500, "to": 500}},
                {"text": " 여기", "offsets": {"from": 500, "to": 900}}, {"text": " 아까", "offsets": {"from": 900, "to": 1200}}]},
    {"offsets": {"from": 2000, "to": 2000}, "text": "  "},
    {"offsets": {"from": 5000, "to": 6000}, "text": " 진짜?", "tokens": []}]}


_noise = [((i * 7919) % 200) - 100 for i in range(8000)]
_tone = [int(6000 * math.sin(2 * math.pi * 220 * i / 8000)) for i in range(8000)]
VOICE_SAMPLES = array.array("h", _noise + _tone).tobytes()


class FakeAnalysis(FakeMedia):
    """Extends the ingest fake with analysis outputs."""

    def __init__(self, fail_on=()):
        super().__init__()
        self.analysis_failures = set(fail_on)

    def __call__(self, command, **kwargs):
        tool, joined = Path(command[0]).name, " ".join(command)
        if tool == "ffmpeg" and "s16le" in command:
            # Raw 8 kHz audio for the voicing track: 1 s of quiet noise, then 1 s of a 220 Hz voice-like tone.
            self.calls.append(command)
            return subprocess.CompletedProcess(command, 0, VOICE_SAMPLES, b"")
        if "analysis" not in joined and not any(f in joined for f in ["ebur128", "silencedetect", "scdet"]):
            return super().__call__(command, **kwargs)
        self.calls.append(command)
        if any(name in joined for name in self.analysis_failures):
            raise RuntimeError(f"{tool} exited 1: fake analysis failure")
        if tool == "whisper-cli":
            Path(command[command.index("-of") + 1] + ".json").write_text(json.dumps(WHISPER), encoding="utf-8")
        elif tool == "sips":
            Path(command[-1]).write_text("thumb")
        elif tool == "ffmpeg" and "ebur128" in joined:
            return subprocess.CompletedProcess(command, 0, "", LOUD_LOG)
        elif tool == "ffmpeg" and "silencedetect" in joined:
            return subprocess.CompletedProcess(command, 0, "", SILENCE_LOG)
        elif tool == "ffmpeg" and "scdet" in joined:
            return subprocess.CompletedProcess(command, 0, "", SCENE_LOG)
        elif tool == "ffmpeg" and "%03d" in command[-1]:
            Path(command[-1].replace("%03d", "001")).write_text("sheet")
        elif tool == "ffmpeg":
            Path(command[-1]).write_text("wav")
        return subprocess.CompletedProcess(command, 0, "", "")


class ParserTests(unittest.TestCase):
    def test_loudness_events_and_reaction_hints(self):
        series = analyze.parse_loudness(LOUD_LOG)
        self.assertEqual(len(series), 80)
        events = analyze.loud_events(series)
        self.assertEqual([(e["start"], e["end"]) for e in events], [(1.6, 2.5), (5.2, 5.9)])
        segments = analyze.parse_transcript(WHISPER)
        labelled = analyze.label_events(events, segments)
        self.assertEqual([e["hint"] for e in labelled], ["reaction", "loud_speech"])
        self.assertEqual(analyze.loud_events([]), [])
        self.assertEqual(analyze.loud_events([(t / 10, -60.0) for t in range(50)]), [])

    def test_hallucinations_are_flagged_and_ignored_for_hints(self):
        segments = [{"start": 0.0, "end": 7.0, "text": "한글자막 by 한효정", "words": []},
                    {"start": 8.0, "end": 9.0, "text": "구독과 좋아요 부탁드려요", "words": []},
                    {"start": 10.0, "end": 12.0, "text": "와 바다 진짜 예쁘다", "words": []},
                    {"start": 13.0, "end": 14.0, "text": "아무 말", "words": []}]
        marked = analyze.mark_suspect(segments, [{"start": 12.8, "end": 16.0}])
        self.assertEqual([s["suspect"] for s in marked], [["known_phrase"], ["known_phrase"], [], ["in_silence"]])
        events = analyze.label_events([{"start": 2.0, "end": 3.0}, {"start": 10.5, "end": 11.5}], marked)
        self.assertEqual([e["hint"] for e in events], ["reaction", "loud_speech"])

    def test_silences_scenes_and_transcript(self):
        self.assertEqual(analyze.parse_silences(SILENCE_LOG), [{"start": 6.5, "end": 9.5}])
        self.assertEqual(analyze.parse_scenes(SCENE_LOG), [{"time": 4.0, "score": 21.7}])
        segments = analyze.parse_transcript(WHISPER)
        self.assertEqual([s["text"] for s in segments], ["여기 아까 왔던 데 아니야?", "진짜?"])
        self.assertEqual([w["text"] for w in segments[0]["words"]], [" 여기", " 아까"])
        self.assertEqual((segments[0]["start"], segments[0]["end"]), (0.5, 1.9))
        self.assertEqual(analyze.clock(3725), "1:02:05")
        self.assertEqual(analyze.clock(65), "01:05")

    def test_asr_model_config(self):
        config = production_config()
        for value in [None, "ggml-large-v3-turbo-q5_0.bin"]:
            config["asr_model"] = value
            with patch.object(production, "ROOT", PROJECT_ROOT):
                pass
        for bad in ["../model.bin", "large.bin", 3, "ggml-x.bin; rm"]:
            with self.subTest(bad=bad):
                config = production_config()
                config["asr_model"] = bad
                with self.assertRaises(ValueError):
                    production.validate_production_config(config)


class AnalyzeRunTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="vlog-analyze-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.trip = self.root / TRIP
        self.trip.mkdir(parents=True)
        for name in ["a-hlg.mov", "b-vfr.mp4", "c-portrait.mp4", "IMG_0001.HEIC"]:
            (self.trip / name).write_text(f"original {name}")
        (self.root / "config").mkdir()
        self.write_config(production_config())
        for module in (common, production):
            root_patch = patch.object(module, "ROOT", self.root)
            root_patch.start()
            self.addCleanup(root_patch.stop)
        self.media = FakeAnalysis()
        with patch.object(ingest, "run_command", side_effect=self.media):
            self.run_id = ingest.ingest(TRIP)["run_id"]
        self.run = self.root / "work" / self.run_id

    def write_config(self, config):
        path = self.root / "config/project.json"
        common.write_json(path, config, replace=path.exists())

    def with_model(self):
        config = production_config()
        config["asr_model"] = "ggml-test.bin"
        self.write_config(config)
        (self.root / ".tools/whisper").mkdir(parents=True)
        (self.root / ".tools/whisper/ggml-test.bin").write_text("fake model")

    def analyze(self, media=None):
        with patch.object(analyze, "run_command", side_effect=media or self.media):
            return analyze.analyze(self.run_id)

    def test_analysis_summarizes_each_clip_with_transcript(self):
        self.with_model()
        state = self.analyze()
        self.assertEqual((state["stage"], state["status"]), ("analyzed", "pending"))
        index = common.read_json(self.run / "analysis/index.json")
        by_id = {c["id"]: c for c in index["clips"]}
        self.assertEqual(by_id["v001"]["transcript"], "done")
        self.assertEqual(by_id["v001"]["reactions"], 1)
        self.assertEqual(by_id["v003"]["transcript"], "not_run: no audio")
        self.assertEqual(index["photo_sheets"], ["sheet-001.jpg"])
        summary = (self.run / "analysis/v001/summary.md").read_text(encoding="utf-8")
        for expected in ["[00:00–00:01] 여기 아까 왔던 데 아니야?", "reaction", "[00:06–00:09]", "00:04 (score 21.7)", "sheet-001.jpg: 00:00–00:03"]:
            self.assertIn(expected, summary)
        self.assertIn("| v001 |", (self.run / "analysis/index.md").read_text(encoding="utf-8"))
        self.assertFalse(list(self.run.glob("analysis/*/audio-16k.wav")))
        self.assertFalse((self.run / ".lock").exists())
        whisper = [c for c in self.media.calls if c[0] == "whisper-cli"]
        self.assertTrue(whisper and all("-l" in c and c[c.index("-l") + 1] == "ko" for c in whisper))
        for command in self.media.calls:
            self.assertFalse(any(f"{os.sep}{ORIGINALS}{os.sep}" in part for part in command if "analysis" in " ".join(command)))

    def test_without_model_signals_still_run(self):
        state = self.analyze()
        self.assertEqual(state["stage"], "analyzed")
        self.assertFalse(any(c[0] == "whisper-cli" for c in self.media.calls))
        clips = common.read_json(self.run / "analysis/index.json")["clips"]
        self.assertTrue(all(c["transcript"].startswith("not_run") for c in clips))
        self.assertIn("없음(대사 없이", (self.run / "analysis/index.md").read_text(encoding="utf-8"))

    def test_missing_configured_model_fails_before_state_change(self):
        config = production_config()
        config["asr_model"] = "ggml-missing.bin"
        self.write_config(config)
        before = (self.run / "state.json").read_bytes()
        with self.assertRaisesRegex(ValueError, "missing"):
            self.analyze()
        self.assertEqual((self.run / "state.json").read_bytes(), before)

    def test_failure_is_recorded_and_retry_keeps_failed_attempt(self):
        with self.assertRaises(RuntimeError):
            self.analyze(FakeAnalysis(fail_on={"scdet"}))
        state = common.read_json(self.run / "state.json")
        self.assertEqual((state["stage"], state["status"]), ("analyze", "failed"))
        self.assertFalse((self.run / ".lock").exists())
        state = self.analyze()
        self.assertEqual(state["stage"], "analyzed")
        self.assertEqual(len(list(self.run.glob("analysis.failed-*"))), 1)
        self.assertNotIn("error", state)

    def test_wrong_stage_scope_and_edited_sources_are_rejected(self):
        self.analyze()
        with self.assertRaisesRegex(ValueError, "ingested run"):
            self.analyze()
        self.write_config(json.loads((PROJECT_ROOT / "config/setup.example.json").read_text()))
        with patch.object(analyze, "run_command", side_effect=AssertionError("No commands allowed")):
            with self.assertRaises(ValueError):
                analyze.analyze(self.run_id)


@unittest.skipUnless(os.environ.get("VLOG_MEDIA_TESTS") == "1", "set VLOG_MEDIA_TESTS=1 (scripts/smoke-media.sh)")
class AnalyzeMediaTests(unittest.TestCase):
    """A synthetic clip with a loud burst and a cut, plus photos. Whisper runs only if VLOG_WHISPER_MODEL is set."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="vlog-analyze-media-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.trip = self.root / TRIP
        self.trip.mkdir(parents=True)
        config = production_config()
        model = os.environ.get("VLOG_WHISPER_MODEL")
        if model:
            config["asr_model"] = Path(model).name
            (self.root / ".tools/whisper").mkdir(parents=True)
            (self.root / ".tools/whisper" / Path(model).name).symlink_to(Path(model).resolve())
        (self.root / "config").mkdir()
        common.write_json(self.root / "config/project.json", config)
        for module in (common, production):
            root_patch = patch.object(module, "ROOT", self.root)
            root_patch.start()
            self.addCleanup(root_patch.stop)
        ffmpeg = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-n"]
        common.run_command(ffmpeg + [
            "-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=30:duration=4",
            "-f", "lavfi", "-i", "color=c=0x426e75:size=1280x720:rate=30:duration=4",
            "-f", "lavfi", "-i", "sine=frequency=330:duration=8,volume='if(between(t,3,3.8),1,0.02)':eval=frame",
            "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]", "-map", "[v]", "-map", "2:a",
            "-c:v", "libx264", "-c:a", "aac", str(self.trip / "burst.mp4")])
        if model:
            speech = self.root / "speech.aiff"
            common.run_command(["say", "-v", "Yuna", "-o", str(speech), "여기 아까 왔던 데 아니야? 진짜 길 잃었다."])
            common.run_command(ffmpeg + ["-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=30:duration=5", "-i", str(speech),
                               "-af", "apad", "-t", "5", "-c:v", "libx264", "-c:a", "aac", str(self.trip / "talk.mp4")])
        png = self.root / "photo.png"
        common.run_command(ffmpeg + ["-f", "lavfi", "-i", "color=c=orange:size=1200x800", "-frames:v", "1", str(png)])
        common.run_command(["sips", "-s", "format", "heic", str(png), "--out", str(self.trip / "IMG_0002.HEIC")])

    def test_real_tools_produce_signals_and_sheets(self):
        run_id = ingest.ingest(TRIP)["run_id"]
        if os.environ.get("VLOG_WHISPER_MODEL"):
            # The symlinked model is a test convenience; production keeps a regular file under .tools/whisper/.
            with patch.object(analyze, "model_path", return_value=Path(os.environ["VLOG_WHISPER_MODEL"]).resolve()):
                state = analyze.analyze(run_id)
        else:
            state = analyze.analyze(run_id)
        run = self.root / "work" / run_id
        signals = common.read_json(run / "analysis/v001/signals.json")
        self.assertEqual(state["stage"], "analyzed")
        self.assertTrue(any(2.5 <= e["start"] <= 3.5 for e in signals["loud_events"]), signals["loud_events"])
        self.assertTrue(any(3.5 <= c["time"] <= 4.5 for c in signals["scene_cuts"]), signals["scene_cuts"])
        self.assertTrue((run / "analysis/v001/sheet-001.jpg").read_bytes().startswith(b"\xff\xd8"))
        self.assertTrue((run / "analysis/photos/sheet-001.jpg").is_file())
        if os.environ.get("VLOG_WHISPER_MODEL"):
            talk = common.read_json(run / "analysis/v002/transcript.json")
            text = " ".join(s["text"] for s in talk["segments"])
            self.assertEqual(talk["status"], "done")
            self.assertTrue("길" in text and ("아까" in text or "왔던" in text), text)
            self.assertFalse(any(s["suspect"] for s in talk["segments"]))
            burst = common.read_json(run / "analysis/v001/transcript.json")["segments"]
            self.assertTrue(all(s["suspect"] for s in burst), burst)
            self.assertTrue(any(e["hint"] == "reaction" for e in signals["loud_events"]), signals["loud_events"])
            print((run / "analysis/v002/summary.md").read_text(encoding="utf-8"))
        print((run / "analysis/v001/summary.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

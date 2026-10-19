"""Ingest contracts. Unit tests use fake commands; media tests run only with VLOG_MEDIA_TESTS=1."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
sys.path.insert(0, str(PROJECT_ROOT / "tests"))
import common
import ingest
import production
from test_production import ORIGINALS, production_config

TRIP = f"{ORIGINALS}/trip"


def stream_probe(width=1280, height=720, rate="30/1", average="30/1", transfer="bt709", audio=True,
                 rotation=None, duration="3.0", codec="h264", created="2026-10-01T10:00:00Z"):
    video = {"codec_type": "video", "codec_name": codec, "width": width, "height": height,
             "r_frame_rate": rate, "avg_frame_rate": average, "color_transfer": transfer, "tags": {}}
    if rotation is not None:
        video["side_data_list"] = [{"rotation": rotation}]
    streams = [video] + ([{"codec_type": "audio", "codec_name": "aac"}] if audio else [])
    return {"streams": streams, "format": {"duration": duration, "tags": {"creation_time": created}}}


class FakeMedia:
    """Stands in for ffprobe/ffmpeg/avconvert/sips and records every call."""

    def __init__(self, fail_on=()):
        self.calls, self.fail_on = [], set(fail_on)
        self.sources = {"a-hlg.mov": stream_probe(transfer="arib-std-b67", codec="hevc", created="2026-10-01T12:00:00Z"),
                        "b-vfr.mp4": stream_probe(average="675/26", created="2026-10-01T09:00:00Z"),
                        "c-portrait.mp4": stream_probe(rotation=-90, audio=False, created="2026-10-01T11:00:00Z")}

    def __call__(self, command, **_kwargs):
        self.calls.append(command)
        tool, target = Path(command[0]).name, command[-1]
        if any(name in " ".join(command) for name in self.fail_on) and tool == "ffmpeg":
            raise RuntimeError("ffmpeg exited 1: fake failure")
        if tool == "ffprobe":
            name = Path(target).name
            payload = stream_probe(1920, 1080) if "proxy" in target else self.sources[name]
            return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")
        if tool == "ffmpeg":
            Path(target).write_text("fake proxy")
        elif tool == "avconvert":
            Path(command[command.index("--output") + 1]).write_text("fake sdr")
        elif tool == "sips" and "--out" in command:
            Path(target).write_text("fake jpeg")
        elif tool == "sips":
            return subprocess.CompletedProcess(command, 0, "  pixelWidth: 4032\n  pixelHeight: 3024\n  format: heic\n  creation: 2026:10:01 19:30:00\n", "")
        return subprocess.CompletedProcess(command, 0, "", "")


class IngestUnitTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="vlog-ingest-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.trip = self.root / TRIP
        self.trip.mkdir(parents=True)
        for name in ["a-hlg.mov", "b-vfr.mp4", "c-portrait.mp4", "IMG_0001.HEIC", "notes.txt", ".DS_Store"]:
            (self.trip / name).write_text(f"original {name}")
        (self.trip / "alias.mp4").symlink_to(self.trip / "b-vfr.mp4")
        (self.root / "config").mkdir()
        common.write_json(self.root / "config/project.json", production_config())
        for module in (common, production):
            root_patch = patch.object(module, "ROOT", self.root)
            root_patch.start()
            self.addCleanup(root_patch.stop)
        self.originals = {p.name: p.read_bytes() for p in self.trip.iterdir() if not p.is_symlink()}
        zone = patch.dict(os.environ, {"TZ": "Asia/Seoul"})
        zone.start()
        time.tzset()
        self.addCleanup(time.tzset)
        self.addCleanup(zone.stop)

    def run_ingest(self, media):
        with patch.object(ingest, "run_command", side_effect=media):
            return ingest.ingest(TRIP)

    def assert_originals_untouched(self):
        self.assertEqual({p.name: p.read_bytes() for p in self.trip.iterdir() if not p.is_symlink()}, self.originals)

    def test_capture_times_normalize_to_utc(self):
        self.assertEqual(ingest.normalize_time("2026-10-01T19:00:00+0900"), "2026-10-01T10:00:00Z")
        self.assertEqual(ingest.normalize_time("2026-10-01T10:00:00.000000Z"), "2026-10-01T10:00:00Z")
        self.assertEqual(ingest.normalize_time("2026:10:01 19:30:00"), "2026-10-01T10:30:00Z")
        self.assertIsNone(ingest.normalize_time("unknown"))

    def test_describe_video_detects_rotation_vfr_and_hdr(self):
        facts = ingest.describe_video(stream_probe(rotation=-90, average="675/26", transfer="arib-std-b67", audio=False))
        self.assertEqual((facts["rotation"], facts["display_size"]), (270, [720, 1280]))
        self.assertTrue(facts["vfr"] and facts["hdr"])
        self.assertFalse(facts["has_audio"])
        steady = ingest.describe_video(stream_probe())
        self.assertFalse(steady["vfr"] or steady["hdr"])
        with self.assertRaises(ValueError):
            ingest.describe_video({"streams": [{"codec_type": "audio"}], "format": {"duration": "1"}})

    def test_ingest_builds_ordered_sources_and_preserves_originals(self):
        state = self.run_ingest(FakeMedia())
        self.assertEqual((state["stage"], state["status"]), ("ingested", "pending"))
        run = self.root / "work" / state["run_id"]
        sources = common.read_json(run / "sources.json")
        self.assertEqual([e["original"].rsplit("/", 1)[1] for e in sources["entries"]],
                         ["b-vfr.mp4", "IMG_0001.HEIC", "c-portrait.mp4", "a-hlg.mov"])
        by_name = {e["original"].rsplit("/", 1)[1]: e for e in sources["entries"]}
        self.assertEqual(by_name["a-hlg.mov"]["color_review"], "needed")
        self.assertTrue(by_name["b-vfr.mp4"]["vfr"])
        self.assertEqual(by_name["c-portrait.mp4"]["display_size"], [720, 1280])
        self.assertEqual(by_name["IMG_0001.HEIC"]["proxy"], "photos/p001.jpg")
        self.assertEqual({s["original"].rsplit("/", 1)[1] for s in sources["skipped"]}, {"notes.txt", "alias.mp4"})
        self.assertEqual(state["counts"], {"video": 3, "photo": 1, "skipped": 2})
        self.assertFalse((run / "tmp").exists())
        self.assertFalse((run / ".lock").exists())
        self.assertEqual(sorted(p.name for p in (run / "proxy").iterdir()), ["v001.mp4", "v002.mp4", "v003.mp4"])
        self.assertEqual(ingest.status(state["run_id"])["status"], "pending")
        self.assert_originals_untouched()

    def test_hdr_goes_through_avconvert_and_only_proxy_paths_are_written(self):
        media = FakeMedia()
        self.run_ingest(media)
        avconvert = [c for c in media.calls if c[0] == "avconvert"]
        self.assertEqual(len(avconvert), 1)
        self.assertTrue(avconvert[0][avconvert[0].index("--source") + 1].endswith("a-hlg.mov"))
        for command in media.calls:
            if command[0] in {"ffmpeg", "avconvert"} or "--out" in command:
                output = command[-1] if command[0] != "avconvert" else command[command.index("--output") + 1]
                self.assertIn(f"{os.sep}work{os.sep}prod-", output)
                self.assertNotIn(ORIGINALS + os.sep, output.split(f"{os.sep}work{os.sep}")[1])

    def test_one_failed_file_is_skipped_with_reason(self):
        state = self.run_ingest(FakeMedia(fail_on={"b-vfr.mp4"}))
        sources = common.read_json(self.root / "work" / state["run_id"] / "sources.json")
        reasons = {s["original"].rsplit("/", 1)[1]: s["reason"] for s in sources["skipped"]}
        self.assertIn("fake failure", reasons["b-vfr.mp4"])
        self.assertEqual(state["counts"]["video"], 2)
        self.assert_originals_untouched()

    def test_all_files_failing_records_failure_and_releases_lock(self):
        for name in ["IMG_0001.HEIC"]:
            (self.trip / name).unlink()
        with self.assertRaisesRegex(ValueError, "No usable"):
            self.run_ingest(FakeMedia(fail_on={".mov", ".mp4"}))
        run = next((self.root / "work").iterdir())
        state = common.read_json(run / "state.json")
        self.assertEqual((state["stage"], state["status"]), ("ingest", "failed"))
        self.assertFalse((run / ".lock").exists())

    def test_setup_phase_and_unlisted_roots_are_rejected_before_any_command(self):
        common.write_json(self.root / "config/project.json",
                          json.loads((PROJECT_ROOT / "config/setup.example.json").read_text()), replace=True)
        with patch.object(ingest, "run_command", side_effect=AssertionError("No commands allowed")):
            with self.assertRaises(ValueError):
                ingest.ingest(TRIP)
            common.write_json(self.root / "config/project.json", production_config(), replace=True)
            for root in [f"{ORIGINALS}/other", ORIGINALS, "work", f"{TRIP}/../other"]:
                with self.subTest(root=root), self.assertRaises(ValueError):
                    ingest.ingest(root)
        self.assertFalse((self.root / "work").exists())

    def test_edited_sources_json_reports_stale(self):
        state = self.run_ingest(FakeMedia())
        path = self.root / "work" / state["run_id"] / "sources.json"
        path.write_text(path.read_text().replace("b-vfr.mp4", "renamed.mp4"))
        self.assertEqual(ingest.status(state["run_id"])["status"], "stale")


@unittest.skipUnless(os.environ.get("VLOG_MEDIA_TESTS") == "1", "set VLOG_MEDIA_TESTS=1 (scripts/smoke-media.sh)")
class IngestMediaTests(unittest.TestCase):
    """Generates synthetic HDR/VFR/rotated/silent clips and photos with FFmpeg and sips; no real media."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="vlog-ingest-media-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.trip = self.root / TRIP
        self.trip.mkdir(parents=True)
        (self.root / "config").mkdir()
        common.write_json(self.root / "config/project.json", production_config())
        for module in (common, production):
            root_patch = patch.object(module, "ROOT", self.root)
            root_patch.start()
            self.addCleanup(root_patch.stop)
        ffmpeg = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-n"]
        source = ["-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=30:duration=3", "-f", "lavfi", "-i", "sine=frequency=440:duration=3"]
        common.run_command(ffmpeg + source + ["-vf", "format=yuv420p10le", "-c:v", "libx265", "-x265-params",
                           "colorprim=bt2020:transfer=arib-std-b67:colormatrix=bt2020nc", "-tag:v", "hvc1",
                           "-color_primaries", "bt2020", "-color_trc", "arib-std-b67", "-colorspace", "bt2020nc",
                           "-c:a", "aac", str(self.trip / "hlg.mov")])
        common.run_command(ffmpeg + ["-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=30:duration=3", "-vf",
                           "setpts='if(lt(N,30),N/30,1+(N-30)/24)/TB'", "-fps_mode", "vfr", "-c:v", "libx264",
                           str(self.trip / "vfr.mp4")])
        plain = self.root / "plain.mp4"
        common.run_command(ffmpeg + ["-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=30:duration=2", "-c:v", "libx264", str(plain)])
        common.run_command(ffmpeg + ["-display_rotation", "90", "-i", str(plain), "-c", "copy", str(self.trip / "portrait.mp4")])
        png = self.root / "photo.png"
        common.run_command(ffmpeg + ["-f", "lavfi", "-i", "color=c=0x426e75:size=1200x800", "-frames:v", "1", str(png)])
        common.run_command(["sips", "-s", "format", "heic", str(png), "--out", str(self.trip / "IMG_0001.HEIC")])
        (self.trip / "notes.txt").write_text("not media")
        self.originals = {p.name: common.digest(p) for p in self.trip.iterdir()}

    def test_real_tools_make_uniform_proxies(self):
        state = ingest.ingest(TRIP)
        run = self.root / "work" / state["run_id"]
        sources = common.read_json(run / "sources.json")
        by_name = {Path(e["original"]).name: e for e in sources["entries"]}
        self.assertEqual(set(by_name), {"hlg.mov", "vfr.mp4", "portrait.mp4", "IMG_0001.HEIC"})
        self.assertTrue(by_name["hlg.mov"]["hdr"] and by_name["vfr.mp4"]["vfr"])
        self.assertEqual(by_name["portrait.mp4"]["display_size"], [720, 1280])
        self.assertFalse(by_name["portrait.mp4"]["has_audio"])
        for name in ["hlg.mov", "vfr.mp4", "portrait.mp4"]:
            with self.subTest(name=name):
                result = ingest.probe(run / by_name[name]["proxy"])
                video = next(s for s in result["streams"] if s["codec_type"] == "video")
                self.assertEqual((video["width"], video["height"], video["codec_name"], video["r_frame_rate"]),
                                 (1920, 1080, "h264", "30/1"))
                self.assertEqual(video.get("color_transfer"), "bt709")
                self.assertAlmostEqual(float(result["format"]["duration"]), by_name[name]["duration_seconds"], delta=0.25)
                self.assertEqual(any(s["codec_type"] == "audio" for s in result["streams"]), by_name[name]["has_audio"])
        self.assertTrue((run / by_name["IMG_0001.HEIC"]["proxy"]).read_bytes().startswith(b"\xff\xd8"))
        self.assertEqual({p.name: common.digest(p) for p in self.trip.iterdir()}, self.originals)
        print(json.dumps({"run": state["run_id"], "counts": state["counts"],
                          "entries": {n: {k: e.get(k) for k in ["proxy", "frames", "vfr", "hdr", "rotation"]}
                                      for n, e in by_name.items()}}, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()

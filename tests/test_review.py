"""Candidate review contracts. Unit tests use fake commands; media tests run only with VLOG_MEDIA_TESTS=1."""
import copy
import json
import os
import shutil
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
import review
from test_analyze import FakeAnalysis
from test_ingest import TRIP
from test_production import production_config

ENTRIES = {"v001": {"id": "v001", "kind": "video", "original": f"{TRIP}/IMG_4512.mp4", "duration_seconds": 60.0,
                    "proxy": "proxy/v001.mp4"},
           "p001": {"id": "p001", "kind": "photo", "original": f"{TRIP}/IMG_0001.HEIC", "proxy": "photos/p001.jpg"}}


def candidates():
    return {"candidates": [
        {"id": "c01", "title": "길 잃고 우왕좌왕 <3바퀴>", "tag": "fun", "source": "v001", "range": [12.0, 41.0],
         "reason": "대사 직후 웃음 후보, 같은 골목 반복", "evidence": ["v001 reaction 00:31"],
         "dialogue": "여기 아까 왔던 데 아니야?", "key_moment": 5.0, "preview": True,
         "plan": {"cuts": [[12.0, 20.0], [30.0, 36.0]], "speed": 1.0, "zoom": 1.2,
                  "captions": [{"kind": "situation", "preset": "box-yellow", "text": "같은 골목 3바퀴째", "at": 0.0, "duration": 3.0, "position": "upper_left"},
                               {"kind": "sfx_text", "preset": "tilt-red", "text": "띠용?!", "at": 4.5, "duration": 1.0, "position": "upper_right"},
                               {"kind": "inner_voice", "preset": "bracket", "text": "(기억력 테스트 실패)", "at": 5.0, "duration": 4.0}],
                  "sfx": [{"name": "띠용", "at": 4.5}], "bgm": "잠깐 멈춤", "notes": ["정적 3초 → 1.2초"]}},
        {"id": "c02", "title": "노을 바다", "tag": "mood", "source": "p001", "key_moment": 2.0,
         "reason": "여행 마지막 장면의 여운", "evidence": [],
         "plan": {"photo_seconds": 4.0, "zoom": 1.1,
                  "captions": [{"kind": "mood", "preset": "serif-fade", "text": "그래도 바람은 좋았다", "at": 0.5, "duration": 3.0}]}}]}


class CandidateContractTests(unittest.TestCase):
    def test_candidates_look_reaches_props_and_page(self):
        data = candidates()
        self.assertIsNone(review.candidates_look(data))
        self.assertNotIn("look", review.render_props(data["candidates"][0], ENTRIES["v001"]))
        data["look"] = {"grade": "warm", "grade_strength": 0.5, "grain": 0.08, "vignette": 0.2}
        items = review.validate_candidates(data, ENTRIES)
        look = review.candidates_look(data)
        self.assertEqual(review.render_props(items[0], ENTRIES["v001"], look=look)["look"], data["look"])
        with tempfile.TemporaryDirectory() as tmp:
            page = review.page_html("prod-x", 1, items, ENTRIES, Path(tmp), look=look)
        self.assertIn("화면 톤: warm 0.5 · grain 0.08 · vignette 0.2", page)
        for bad in [{"grade": "teal"}, {"grain": 1}, False]:
            with self.subTest(look=bad), self.assertRaises(ValueError):
                review.candidates_look({"look": bad})
            with self.subTest(candidates_look=bad), self.assertRaises(ValueError):
                review.validate_candidates({**data, "look": bad}, ENTRIES)

    def test_valid_candidates_and_frame_plan(self):
        items = review.validate_candidates(candidates(), ENTRIES)
        self.assertEqual(review.edited_seconds(items[0], ENTRIES["v001"]), 14.0)
        self.assertEqual(review.edited_to_source(items[0], 0.0), 12.0)
        self.assertEqual(review.edited_to_source(items[0], 9.0), 31.0)
        props = review.render_props(items[0], ENTRIES["v001"])
        self.assertEqual([(s["trimBefore"], s["frames"]) for s in props["segments"]], [(360, 240), (900, 180)])
        self.assertEqual((props["durationInFrames"], props["keyFrame"]), (420, 150))
        self.assertEqual([(c["from"], c["duration"]) for c in props["captions"]], [(0, 90), (135, 30), (150, 120)])
        photo = review.render_props(items[1], ENTRIES["p001"])
        self.assertEqual((photo["kind"], photo["durationInFrames"], photo["keyFrame"]), ("image", 120, 60))
        fast = copy.deepcopy(items[0])
        fast["plan"]["speed"] = 2.0
        self.assertEqual(review.render_props(fast, ENTRIES["v001"])["durationInFrames"], 210)

    def test_invalid_candidates_rejected(self):
        changes = [
            lambda d: d["candidates"][1].update(id="c01"),
            lambda d: d["candidates"][0].update(id="x1"),
            lambda d: d["candidates"][0].update(tag="sad"),
            lambda d: d["candidates"][0].update(reason=" "),
            lambda d: d["candidates"][0].update(source="v999"),
            lambda d: d["candidates"][0].update(range=[12.0, 70.0]),
            lambda d: d["candidates"][0]["plan"].update(cuts=[[30.0, 36.0], [12.0, 20.0]]),
            lambda d: d["candidates"][0]["plan"].update(cuts=[[12.0, 12.1]]),
            lambda d: d["candidates"][0]["plan"].update(cuts=[[10.0, 20.0]]),
            lambda d: d["candidates"][0]["plan"].update(speed=8),
            lambda d: d["candidates"][0]["plan"].update(zoom=0.5),
            lambda d: d["candidates"][0].update(key_moment=20.0),
            lambda d: d["candidates"][0]["plan"]["captions"][0].update(kind="editorial"),
            lambda d: d["candidates"][0]["plan"]["captions"][0].update(text=""),
            lambda d: d["candidates"][0]["plan"]["captions"][0].update(at=13.5, duration=2.0),
            lambda d: d["candidates"][0]["plan"]["captions"][0].update(position="offscreen"),
            lambda d: d["candidates"][0]["plan"]["sfx"][0].update(at=99),
            lambda d: d["candidates"][0].update(preview="yes"),
            lambda d: d["candidates"][0].update(evidence="one"),
            lambda d: d["candidates"][1].update(range=[0, 1]),
            lambda d: d["candidates"][1]["plan"].update(photo_seconds=30),
            lambda d: d.update(candidates=[]),
        ]
        for index, change in enumerate(changes):
            with self.subTest(index=index):
                data = candidates()
                change(data)
                with self.assertRaises(ValueError):
                    review.validate_candidates(data, ENTRIES)

    def test_page_escapes_text_and_has_no_scripts(self):
        items = review.validate_candidates(candidates(), ENTRIES)
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "c01").mkdir()
            (folder / "c01/preview.mp4").write_text("clip")
            page = review.page_html("prod-x", 1, items, ENTRIES, folder)
        self.assertIn("&lt;3바퀴&gt;", page)
        self.assertNotIn("<script", page.lower())
        self.assertIn('src="c01/expected.jpg"', page)
        self.assertIn('src="c01/preview.mp4"', page)
        self.assertNotIn('src="c02/preview.mp4"', page)
        self.assertIn("c02 제외", page)
        self.assertIn("fun 1 · mood 1", page)

    def test_selection_contract(self):
        items = review.validate_candidates(candidates(), ENTRIES)
        good = {"decisions": {"c01": {"decision": "caption_edit", "note": "띠용 대신 엥?"}, "c02": {"decision": "adopt"}}}
        self.assertEqual(set(review.validate_selection(good, items)), {"c01", "c02"})
        for bad in [{"decisions": {"c01": {"decision": "adopt"}}},
                    {"decisions": {"c01": {"decision": "caption_edit"}, "c02": {"decision": "adopt"}}},
                    {"decisions": {"c01": {"decision": "maybe"}, "c02": {"decision": "adopt"}}},
                    {"decisions": {"c01": {"decision": "drop"}, "c02": {"decision": "drop"}}}]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                review.validate_selection(bad, items)


class FakeReview(FakeAnalysis):
    def __call__(self, command, **kwargs):
        tool = Path(command[0]).name
        if tool == "node" and command[1].endswith("review.mjs"):
            self.calls.append(command)
            run = common.ROOT / "work" / command[2]
            folder = run / "review" / f"v{command[3]}"
            for job in json.loads((folder / "render-input.json").read_text())["jobs"]:
                (folder / job["id"] / "expected.jpg").write_text("still")
                if job["preview"]:
                    (folder / job["id"] / "preview.mp4").write_text("clip")
            return subprocess.CompletedProcess(command, 0, "", "")
        if tool == "ffmpeg" and "-ss" in command:
            self.calls.append(command)
            Path(command[-1]).write_text("frame")
            return subprocess.CompletedProcess(command, 0, "", "")
        return super().__call__(command, **kwargs)


class ReviewRunTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="vlog-review-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        trip = self.root / TRIP
        trip.mkdir(parents=True)
        for name in ["a-hlg.mov", "IMG_0001.HEIC"]:
            (trip / name).write_text(f"original {name}")
        (self.root / "config").mkdir()
        common.write_json(self.root / "config/project.json", production_config())
        for module in (common, production):
            root_patch = patch.object(module, "ROOT", self.root)
            root_patch.start()
            self.addCleanup(root_patch.stop)
        self.media = FakeReview()
        with patch.object(ingest, "run_command", side_effect=self.media):
            self.run_id = ingest.ingest(TRIP)["run_id"]
        with patch.object(analyze, "run_command", side_effect=self.media):
            analyze.analyze(self.run_id)
        self.run = self.root / "work" / self.run_id
        data = candidates()
        data["candidates"][0]["range"] = [0.0, 3.0]
        data["candidates"][0]["key_moment"] = 1.0
        data["candidates"][0]["plan"].update(cuts=[[0.0, 1.0], [1.5, 3.0]], captions=[
            {"kind": "variety", "preset": "pop", "text": "결국 원점", "at": 0.5, "duration": 1.0}], sfx=[])
        common.write_json(self.run / "candidates.json", data)

    def build(self, media=None):
        with patch.object(review, "run_command", side_effect=media or self.media):
            return review.build(self.run_id)

    def test_build_creates_versioned_cards_and_select_records_choice(self):
        state = self.build()
        self.assertEqual((state["stage"], state["status"], state["review_version"]), ("reviewed", "pending", 1))
        folder = self.run / "review/v1"
        self.assertEqual(sorted(p.name for p in (folder / "c01").iterdir()),
                         ["expected.jpg", "preview.mp4", "src-1.jpg", "src-2.jpg", "src-3.jpg", "src-4.jpg"])
        self.assertEqual(sorted(p.name for p in (folder / "c02").iterdir()), ["expected.jpg", "src-1.jpg"])
        jobs = common.read_json(folder / "render-input.json")["jobs"]
        self.assertEqual(jobs[0]["props"]["segments"][0]["src"], "proxy/v001.mp4")
        self.assertIn("결국 원점", (folder / "index.html").read_text(encoding="utf-8"))
        self.assertEqual(self.build()["review_version"], 2)
        self.assertTrue((folder / "index.html").is_file())
        common.write_json(self.run / "selection.json", {"decisions": {"c01": {"decision": "adopt"}, "c02": {"decision": "drop"}}})
        state = review.select(self.run_id)
        self.assertEqual((state["stage"], state["counts_selected"]), ("selected", {"adopt": 1, "caption_edit": 0, "drop": 1}))
        self.assertFalse((self.run / ".lock").exists())

    def test_render_failure_is_recorded_and_rebuild_uses_new_version(self):
        broken = FakeReview(fail_on={"review.mjs"})
        broken.analysis_failures = set()

        def failing(command, **kwargs):
            if command[0] == "node":
                raise RuntimeError("node exited 1: fake render failure")
            return broken(command, **kwargs)
        with self.assertRaises(RuntimeError):
            self.build(failing)
        state = common.read_json(self.run / "state.json")
        self.assertEqual((state["stage"], state["status"]), ("review", "failed"))
        self.assertEqual(self.build()["review_version"], 2)
        self.assertTrue((self.run / "review/v1").is_dir())

    def test_edited_candidates_after_review_block_selection(self):
        self.build()
        data = common.read_json(self.run / "candidates.json")
        data["candidates"][0]["title"] = "바뀐 제목"
        common.write_json(self.run / "candidates.json", data, replace=True)
        common.write_json(self.run / "selection.json", {"decisions": {"c01": {"decision": "adopt"}, "c02": {"decision": "adopt"}}})
        with self.assertRaisesRegex(ValueError, "changed after the review"):
            review.select(self.run_id)

    def test_wrong_stage_and_setup_scope_rejected(self):
        with self.assertRaisesRegex(ValueError, "reviewed run"):
            review.select(self.run_id)
        common.write_json(self.root / "config/project.json",
                          json.loads((PROJECT_ROOT / "config/setup.example.json").read_text()), replace=True)
        with patch.object(review, "run_command", side_effect=AssertionError("No commands allowed")):
            with self.assertRaises(ValueError):
                review.build(self.run_id)


@unittest.skipUnless(os.environ.get("VLOG_MEDIA_TESTS") == "1", "set VLOG_MEDIA_TESTS=1 (scripts/smoke-media.sh)")
class ReviewMediaTests(unittest.TestCase):
    """Renders real expected stills and a preview clip with Remotion from synthetic media."""

    def setUp(self):
        keep = os.environ.get("VLOG_KEEP_REVIEW_DIR")
        self.root = Path(tempfile.mkdtemp(prefix="vlog-review-media-", dir=keep)).resolve()
        if not keep:
            self.addCleanup(shutil.rmtree, self.root, True)
        trip = self.root / TRIP
        trip.mkdir(parents=True)
        (self.root / "config").mkdir()
        common.write_json(self.root / "config/project.json", production_config())
        for name in [".tools", "renderer"]:
            (self.root / name).symlink_to(PROJECT_ROOT / name)
        for module in (common, production):
            root_patch = patch.object(module, "ROOT", self.root)
            root_patch.start()
            self.addCleanup(root_patch.stop)
        ffmpeg = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-n"]
        common.run_command(ffmpeg + ["-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=30:duration=6",
                           "-f", "lavfi", "-i", "sine=frequency=330:duration=6", "-c:v", "libx264", "-c:a", "aac",
                           str(trip / "alley.mp4")])
        png = self.root / "sunset.png"
        common.run_command(ffmpeg + ["-f", "lavfi", "-i", "gradients=s=1200x800:c0=0xff8a3d:c1=0x2b3a67:d=1",
                           "-frames:v", "1", str(png)])
        common.run_command(["sips", "-s", "format", "heic", str(png), "--out", str(trip / "IMG_0001.HEIC")])

    def test_expected_stills_and_preview_render(self):
        run_id = ingest.ingest(TRIP)["run_id"]
        with patch.object(analyze, "model_path", return_value=None):
            analyze.analyze(run_id)
        run = self.root / "work" / run_id
        data = candidates()
        data["candidates"][0].update(source="v001", range=[0.5, 5.5], key_moment=2.2)
        data["candidates"][0]["plan"]["cuts"] = [[0.5, 2.5], [3.5, 5.5]]
        data["candidates"][0]["plan"]["sfx"] = [{"name": "띠용", "at": 1.8}]
        data["candidates"][0]["plan"]["captions"] = [
            {"kind": "situation", "preset": "box-yellow", "text": "같은 골목 3바퀴째", "at": 0.0, "duration": 3.5, "position": "upper_left"},
            {"kind": "sfx_text", "preset": "tilt-red", "text": "띠용?!", "at": 1.8, "duration": 1.2, "position": "upper_right"},
            {"kind": "variety", "preset": "pop", "text": "결국 원점", "at": 2.0, "duration": 1.5},
            {"kind": "inner_voice", "preset": "bracket", "text": "(기억력 테스트 실패)", "at": 2.0, "duration": 1.8, "position": "center"}]
        common.write_json(run / "candidates.json", data)
        state = review.build(run_id)
        folder = run / "review/v1"
        for cid in ["c01", "c02"]:
            probe = ingest.probe(folder / cid / "expected.jpg")
            self.assertEqual((probe["streams"][0]["width"], probe["streams"][0]["height"]), (1920, 1080))
        clip = ingest.probe(folder / "c01/preview.mp4")
        video = next(s for s in clip["streams"] if s["codec_type"] == "video")
        self.assertEqual((video["width"], video["height"]), (960, 540))
        self.assertAlmostEqual(float(clip["format"]["duration"]), 4.0, delta=0.15)
        self.assertTrue(any(s["codec_type"] == "audio" for s in clip["streams"]))
        print(json.dumps({"page": state["page"]}, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()

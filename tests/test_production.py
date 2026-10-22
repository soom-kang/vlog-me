"""Production scope, timeline v2 and source-protection contracts. Text fixtures only."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
import common
import production
import synthetic

HOOK = PROJECT_ROOT / ".claude/hooks/protect_sources.py"
ORIGINALS = "sources"


def production_config():
    return {"project": "vlog-me", "agent_runtime": "claude-code", "phase": "production", "use_subagents": False,
            "source_roots": [f"{ORIGINALS}/trip"], "runtime_policy": "content_driven",
            "target_duration_seconds": None, "external_processing": False, "upload": False,
            "asr_local": True, "audio_search": False, "audio_downloads": False, "production_render": False,
            "production_profile": {"width": 1920, "height": 1080, "fps": 30, "color": "SDR BT.709",
                                   "concurrency": 4, "timeout_seconds": 3600}}


def edit_fixture():
    sources = {"v1": {"kind": "video", "frames": 300, "has_audio": True},
               "v2": {"kind": "video", "frames": 90, "has_audio": False},
               "p1": {"kind": "image"},
               "bgm": {"kind": "audio", "frames": 600},
               "boing": {"kind": "audio", "frames": 15}}
    timeline = {"schema_version": 2, "purpose": "production", "fps": 30, "width": 1920, "height": 1080,
        "duration_frames": 240,
        "clips": [
            {"id": "c1", "source": "v1", "from": 0, "duration": 120, "in": 30, "speed": 1.5, "zoom": 1.2, "tag": "fun"},
            {"id": "c2", "source": "v2", "from": 120, "duration": 60, "in": 0, "tag": "mood", "transition": "fade"},
            {"id": "c3", "source": "p1", "from": 180, "duration": 60, "tag": "mood"}],
        "audio": [
            {"id": "o1", "kind": "original", "clip": "c1", "from": 0, "duration": 120, "gain_db": [[0, 0], [119, 0]]},
            {"id": "b1", "kind": "bgm", "source": "bgm", "from": 0, "duration": 240, "in": 0,
             "gain_db": [[0, -60], [15, -18], [120, -24], [239, -60]]},
            {"id": "s1", "kind": "sfx", "source": "boing", "from": 60, "duration": 15, "gain_db": [[0, -6], [14, -6]]}],
        "captions": [
            {"id": "t1", "kind": "situation", "preset": "box-yellow", "text": "같은 골목 3바퀴째", "from": 0, "duration": 60, "position": "upper_left"},
            {"id": "t2", "kind": "sfx_text", "preset": "tilt-red", "text": "띠용?!", "from": 60, "duration": 15, "position": "upper_right"},
            {"id": "t3", "kind": "inner_voice", "preset": "bracket", "text": "(기억력 테스트 실패)", "from": 75, "duration": 45},
            {"id": "t4", "kind": "variety", "preset": "pop", "text": "결국 원점", "from": 100, "duration": 20},
            {"id": "t5", "kind": "mood", "preset": "serif-fade", "text": "그래도 바람은 좋았다", "from": 180, "duration": 60}]}
    return timeline, sources


class ProductionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="vlog-production-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        (self.root / ORIGINALS / "trip").mkdir(parents=True)
        (self.root / ORIGINALS / "trip/IMG_0001.mp4").write_text("original placeholder")
        for module in (common, production, synthetic):
            root_patch = patch.object(module, "ROOT", self.root)
            root_patch.start()
            self.addCleanup(root_patch.stop)

    def test_production_config_accepts_only_bounded_scope(self):
        production.validate_production_config(production_config())
        changes = [{"phase": "setup_synthetic_only"}, {"upload": True}, {"external_processing": True},
                   {"use_subagents": True}, {"source_roots": []}, {"source_roots": ["raw/trip"]},
                   {"source_roots": [ORIGINALS]}, {"source_roots": [f"{ORIGINALS}/../work"]},
                   {"source_roots": ["/Users/someone/Movies"]}, {"audio_downloads": "yes"},
                   {"target_duration_seconds": 900}]
        for change in changes:
            with self.subTest(change=change):
                config = production_config()
                config.update(change)
                with self.assertRaises(ValueError):
                    production.validate_production_config(config)
        for key, value in [("concurrency", 9), ("timeout_seconds", 0), ("width", 3840)]:
            with self.subTest(profile=key):
                config = production_config()
                config["production_profile"][key] = value
                with self.assertRaises(ValueError):
                    production.validate_production_config(config)

    def test_example_config_is_valid_once_a_trip_folder_is_named(self):
        example = json.loads((PROJECT_ROOT / "config/production.example.json").read_text())
        with self.assertRaises(ValueError):
            production.validate_production_config(example)
        example["source_roots"] = [f"{ORIGINALS}/trip"]
        production.validate_production_config(example)

    def test_phases_are_exclusive(self):
        with self.assertRaises(ValueError):
            common.validate_setup_config(production_config())
        setup = json.loads((PROJECT_ROOT / "config/setup.example.json").read_text())
        with self.assertRaises(ValueError):
            production.validate_production_config(setup)

    def test_production_run_ids_are_separate_from_synthetic(self):
        self.assertEqual(production.production_run_path("prod-20261019-trip").name, "prod-20261019-trip")
        for name in ["synthetic-abc", "episode-001", "prod-../../raw", "prod-", "PROD-x", None]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                production.production_run_path(name)
        with self.assertRaises(ValueError):
            common.run_path("prod-20261019-trip")

    def test_sources_resolve_only_inside_allowed_roots(self):
        config = production_config()
        found = production.source_path(config, f"{ORIGINALS}/trip/IMG_0001.mp4")
        self.assertEqual(found, self.root / ORIGINALS / "trip/IMG_0001.mp4")
        (self.root / ORIGINALS / "other").mkdir()
        (self.root / ORIGINALS / "other/x.mp4").write_text("not allowed")
        (self.root / ORIGINALS / "trip/alias.mp4").symlink_to(self.root / ORIGINALS / "other/x.mp4")
        os.link(self.root / ORIGINALS / "trip/IMG_0001.mp4", self.root / ORIGINALS / "trip/hard.mp4")
        for relative in [f"{ORIGINALS}/other/x.mp4", f"{ORIGINALS}/trip/../other/x.mp4", f"{ORIGINALS}/trip",
                         f"{ORIGINALS}/trip/alias.mp4", f"{ORIGINALS}/trip/hard.mp4", f"{ORIGINALS}/trip/missing.mp4",
                         "/etc/hosts", "work/x.mp4"]:
            with self.subTest(relative=relative), self.assertRaises(ValueError):
                production.source_path(config, relative)

    def test_current_production_scope_is_read_from_config(self):
        (self.root / "config").mkdir()
        common.write_json(self.root / "config/project.json", production_config())
        self.assertEqual(production.require_production_scope()["phase"], "production")
        with self.assertRaises(ValueError):
            common.require_setup_scope()


class TimelineV2Tests(unittest.TestCase):
    def test_production_example_has_mood_direction(self):
        example = common.read_json(PROJECT_ROOT / "config/production.example.json")
        self.assertEqual(example["caption_style"], "mood 90 / variety 10")
        self.assertEqual(example["editorial_direction"],
                         "mood 90 / fun 10, quiet scenery and first-person narration with a light touch of everyday humor")

    def test_dissolve_and_drift_rules(self):
        timeline, sources = edit_fixture()
        timeline["clips"][1]["transition"] = "dissolve"
        timeline["clips"][0]["drift"] = True
        self.assertEqual(production.validate_timeline_v2(timeline, sources), 240)
        sources["v1"]["frames"] = 233
        self.assertEqual(production.validate_timeline_v2(timeline, sources), 240)
        sources["v1"]["frames"] = 232
        with self.assertRaisesRegex(ValueError, "Dissolve needs D more"):
            production.validate_timeline_v2(timeline, sources)
        sources["v1"]["frames"] = 210
        with self.assertRaisesRegex(ValueError, "Dissolve needs D more"):
            production.validate_timeline_v2(timeline, sources)
        for index, update, message in [(0, {"transition": "dissolve"}, "First clip"),
                                       (2, {"drift": False}, "Photos already drift"),
                                       (0, {"drift": "yes"}, "drift must")]:
            timeline, sources = edit_fixture()
            timeline["clips"][index].update(update)
            with self.subTest(update=update), self.assertRaisesRegex(ValueError, message):
                production.validate_timeline_v2(timeline, sources)
        timeline, sources = edit_fixture()
        timeline["clips"][1].update(transition="dissolve", duration=14)
        with self.assertRaisesRegex(ValueError, "both clips"):
            production.validate_timeline_v2(timeline, sources)

    def test_narration_and_light_leak_minimums(self):
        timeline, sources = edit_fixture()
        timeline["captions"] = [{"id": "n1", "kind": "narration", "preset": "diary", "text": "바람이 불었다",
                                 "from": 0, "duration": 74}]
        with self.assertRaisesRegex(ValueError, "Narration duration"):
            production.validate_timeline_v2(timeline, sources)
        timeline["captions"][0]["duration"] = 75
        self.assertEqual(production.validate_timeline_v2(timeline, sources), 240)
        timeline["effects"] = [{"id": "fx1", "type": "light_leak", "from": 0, "duration": 14, "strength": 2}]
        with self.assertRaisesRegex(ValueError, "Light leak"):
            production.validate_timeline_v2(timeline, sources)
        timeline["effects"][0]["duration"] = 15
        self.assertEqual(production.validate_timeline_v2(timeline, sources), 240)

    def test_existing_fixture_still_valid(self):
        timeline, sources = edit_fixture()
        self.assertNotIn("look", timeline)
        self.assertEqual(production.validate_timeline_v2(timeline, sources), 240)

    def test_look_is_optional_and_bounded(self):
        timeline, sources = edit_fixture()
        good = {"grade": "warm", "grade_strength": 0.5, "grain": 0.08, "vignette": 0.2, "letterbox": 2.39}
        self.assertEqual(production.validate_timeline_v2({**timeline, "look": good}, sources), 240)
        self.assertEqual(production.validate_look({}), {})
        self.assertEqual(production.validate_look({"letterbox": None}), {"letterbox": None})
        for bad in [None, [], {"grade": "teal"}, {"grain": 0.3}, {"vignette": True}, {"letterbox": 1.85},
                    {"lut": "file"}, {"grade_strength": 1.2}, {"grain": float("nan")}, {"vignette": float("inf")},
                    {"grade_strength": -0.1}, {"grain": "0.1"}, {"letterbox": True}]:
            with self.subTest(look=bad), self.assertRaises(ValueError):
                production.validate_timeline_v2({**timeline, "look": bad}, sources)

    def test_valid_edit_is_content_driven(self):
        timeline, sources = edit_fixture()
        self.assertEqual(production.validate_timeline_v2(timeline, sources), 240)

    def test_invalid_edits_rejected(self):
        changes = [
            lambda t: t.update(schema_version=1),
            lambda t: t.update(duration_frames=300),
            lambda t: t.update(width=1280),
            lambda t: t["clips"][1].update(**{"from": 121}),
            lambda t: t["clips"][0].update(tag="other"),
            lambda t: t["clips"][0].update(speed=5),
            lambda t: t["clips"][0].update(**{"in": 200}),
            lambda t: t["clips"][0].update(zoom=0.5),
            lambda t: t["clips"][2].update(speed=1),
            lambda t: t["clips"][0].update(transition="spin"),
            lambda t: t["audio"].pop(0),
            lambda t: t["audio"].append(dict(t["audio"][0], id="o-dup")),
            lambda t: t["audio"][0].update(clip="c3"),
            lambda t: t["audio"][0].update(duration=100, gain_db=[[0, 0], [99, 0]]),
            lambda t: t["audio"][1].update(source="v1"),
            lambda t: t["audio"][1].update(duration=240, **{"in": 400}),
            lambda t: t["audio"][2].update(gain_db=[[0, -6], [14, 3]]),
            lambda t: t["audio"][2].update(gain_db=[[0, -6], [13, -6]]),
            lambda t: t["audio"][2].update(kind="voiceover"),
            lambda t: t["captions"][0].update(kind="editorial"),
            lambda t: t["captions"][0].update(preset=""),
            lambda t: t["captions"][0].update(text="  "),
            lambda t: t["captions"][0].update(position="offscreen"),
            lambda t: t["captions"][4].update(duration=61),
            lambda t: t["captions"][1].update(id="t1"),
        ]
        for index, change in enumerate(changes):
            with self.subTest(index=index):
                timeline, sources = edit_fixture()
                change(timeline)
                with self.assertRaises(ValueError):
                    production.validate_timeline_v2(timeline, sources)

    def test_silent_video_needs_no_original_cue_but_sound_video_does(self):
        timeline, sources = edit_fixture()
        sources["v2"]["has_audio"] = True
        with self.assertRaises(ValueError):
            production.validate_timeline_v2(timeline, sources)
        timeline["audio"].append({"id": "o2", "kind": "original", "clip": "c2", "from": 120, "duration": 60,
                                  "gain_db": [[0, -80], [59, -80]]})
        self.assertEqual(production.validate_timeline_v2(timeline, sources), 240)

    def test_caption_share_is_reported_not_enforced(self):
        timeline, _ = edit_fixture()
        share = production.caption_style_share(timeline)
        self.assertEqual((share["mood"], share["variety"], share["mood_share"]), (1, 4, 0.2))
        timeline["captions"] = [dict(timeline["captions"][4], id=f"m{i}") for i in range(3)]
        self.assertEqual(production.caption_style_share(timeline)["mood_share"], 1.0)
        self.assertTrue(production.caption_style_share(timeline)["in_window"])

    def test_synthetic_v1_validator_still_rejects_production_timelines(self):
        timeline, _ = edit_fixture()
        with self.assertRaises(ValueError):
            common.validate_timeline(timeline, {"assets": {}})


class SourceHookTests(unittest.TestCase):
    def run_hook(self, tool, **tool_input):
        event = {"tool_name": tool, "tool_input": tool_input, "cwd": str(PROJECT_ROOT)}
        result = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(event), capture_output=True,
                                text=True, env={**os.environ, "CLAUDE_PROJECT_DIR": str(PROJECT_ROOT)})
        return result.returncode

    def test_reads_and_derived_outputs_pass(self):
        for command in [f"ffprobe -v error {ORIGINALS}/trip/a.mp4 > work/prod-x/a.json 2>&1",
                        f"ffmpeg -i {ORIGINALS}/trip/a.mp4 -c:v h264_videotoolbox work/prod-x/proxy/a.mp4",
                        f"sips -s format jpeg {ORIGINALS}/trip/IMG_1.HEIC --out work/prod-x/photos/IMG_1.jpg",
                        "ls resources/ && rm work/prod-x/tmp.txt", "git status --short"]:
            with self.subTest(command=command):
                self.assertEqual(self.run_hook("Bash", command=command), 0)
        self.assertEqual(self.run_hook("Write", file_path=str(PROJECT_ROOT / "work/prod-x/note.md")), 0)

    def test_writes_into_sources_are_blocked(self):
        for command in [f"ffmpeg -y -i work/a.mp4 {ORIGINALS}/trip/a.mp4", f"rm -rf {ORIGINALS}/trip",
                        f"echo hi > {ORIGINALS}/trip/x.txt", f"cd {ORIGINALS}/trip && touch x",
                        f"sips -s format jpeg work/a.HEIC --out {ORIGINALS}/trip/a.jpg",
                        f"cp work/a.mp4 ./{ORIGINALS}/trip/", f"sed -i '' s/a/b/ {ORIGINALS}/trip/notes.txt"]:
            with self.subTest(command=command):
                self.assertEqual(self.run_hook("Bash", command=command), 2)
        for path in [f"{ORIGINALS}/trip/note.md", str(PROJECT_ROOT / ORIGINALS / "trip/note.md")]:
            with self.subTest(path=path):
                self.assertEqual(self.run_hook("Edit", file_path=path), 2)

    def test_malformed_input_passes_through(self):
        result = subprocess.run([sys.executable, str(HOOK)], input="not json", capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()

"""Caption preset registry, mood-first ratio reporting and bundled font integrity. Text fixtures only."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
sys.path.insert(0, str(PROJECT_ROOT / "tests"))
import doctor
import production
import review
from test_review import ENTRIES, candidates

REGISTRY = production.CAPTION_REGISTRY


class PresetRegistryTests(unittest.TestCase):
    def test_renderer_implements_exactly_the_registered_presets(self):
        source = (PROJECT_ROOT / "renderer/src/production/Captions.tsx").read_text(encoding="utf-8")
        implemented = set()
        for block in ["const STYLES", "const LAYOUTS"]:
            body = source.split(block, 1)[1].split("\n};", 1)[0]
            implemented |= set(re.findall(r"^  '?([a-z][a-z-]*)'?: [a-zA-Z(]", body, re.M))
        registered = {preset for spec in REGISTRY["kinds"].values() for preset in spec["presets"]}
        self.assertEqual(implemented, registered)

    def test_groups_cover_variety_mood_and_dialogue(self):
        groups = {spec["group"] for spec in REGISTRY["kinds"].values()}
        self.assertEqual(groups, {"variety", "mood", "dialogue"})
        self.assertEqual(REGISTRY["target_mood_share"], 0.95)
        self.assertNotIn("target_variety_share", REGISTRY)

    def test_caption_text_rules(self):
        self.assertEqual(production.validate_caption_text({"kind": "sfx_text", "text": "쾅"}, require_preset=False), "pen-sfx")
        self.assertEqual(production.validate_caption_text({"kind": "variety", "preset": "shout", "text": "실화냐\n이게"}), "shout")
        bad = [{"kind": "variety", "text": "결국 원점"},
               {"kind": "variety", "preset": "serif-fade", "text": "결국 원점"},
               {"kind": "sfx_text", "preset": "burst", "text": "띠용띠용띠용띠용띠용"},
               {"kind": "variety", "preset": "pop", "text": "한 줄\n두 줄\n세 줄"},
               {"kind": "editorial", "preset": "pop", "text": "옛 kind"},
               {"kind": "mood", "preset": "serif-fade", "text": "바람", "position": "offscreen"}]
        for caption in bad:
            with self.subTest(caption=caption), self.assertRaises(ValueError):
                production.validate_caption_text(caption)

    def test_share_is_reported_against_the_window(self):
        def share(kinds):
            return production.caption_style_share({"captions": [{"kind": k} for k in kinds]})
        self.assertTrue(share(["mood"] * 9 + ["variety"])["in_window"])
        self.assertFalse(share(["variety"] * 5 + ["mood"] * 5)["in_window"])
        self.assertTrue(share(["mood"] * 10)["in_window"])
        self.assertFalse(share(["variety"] * 10)["in_window"])
        self.assertIsNone(share(["dialogue"])["mood_share"])

    def test_narration_allows_four_lines_of_22(self):
        cue = {"kind": "narration", "preset": "diary", "text": "\n".join(["가" * 22] * 4)}
        self.assertEqual(production.validate_caption_text(cue), "diary")
        for text in ["\n".join(["가"] * 5), "가" * 23]:
            with self.subTest(text=text), self.assertRaises(ValueError):
                production.validate_caption_text({**cue, "text": text})
        with self.assertRaises(ValueError):
            production.validate_caption_text({"kind": "mood", "preset": "serif-fade", "text": "가\n나\n다"})

    def test_mood_friendly_defaults(self):
        # House style (docs/house-style.md): spoken-tone reference presets are the defaults.
        expected = {"variety": "deadpan", "situation": "box-dark", "sfx_text": "pen-sfx", "inner_voice": "pen-note",
                    "dialogue": "talk", "mood": "talk-mood", "narration": "talk-note", "place": "place-tiny"}
        for kind, preset in expected.items():
            with self.subTest(kind=kind):
                self.assertEqual(production.validate_caption_text({"kind": kind, "text": "가"}, require_preset=False), preset)

    def test_old_presets_still_registered(self):
        old = {"pop", "shout", "punch", "drop", "shake", "box-yellow", "box-dark", "box-pink", "box-mint", "box-sky",
               "ribbon", "sticker", "stamp", "bubble", "tilt-red", "tilt-blue", "burst", "whoosh", "pen-sfx",
               "bracket", "whisper", "thought", "pen-note", "dialogue", "dialogue-box", "serif-fade", "serif-low",
               "editorial", "letter-fade", "film-line", "pen-script", "place-card", "place-editorial"}
        registered = {p for spec in REGISTRY["kinds"].values() for p in spec["presets"]}
        self.assertEqual(len(old), 33)
        self.assertTrue(old <= registered)
        self.assertEqual(len(registered), 48)

    def test_reference_talk_presets(self):
        # Spoken-tone presets modelled on the 오눅·걍민경 references; kind defaults stay mood-first.
        cues = {"talk": "dialogue", "talk-note": "narration", "talk-mood": "mood", "place-tiny": "place", "pop-word": "variety"}
        for preset, kind in cues.items():
            with self.subTest(preset=preset):
                self.assertEqual(production.validate_caption_text({"kind": kind, "preset": preset, "text": "미쳐"}), preset)
        self.assertEqual(production.validate_caption_text(
            {"kind": "narration", "preset": "talk-note", "text": "오일은 직접 고를 수 있어요\n저는 코코넛으로!"}), "talk-note")
        for kind in ["mood", "narration", "place"]:
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                production.validate_caption_text({"kind": kind, "preset": "talk", "text": "가"})

    def test_narration_reading_time(self):
        text = "가나다라마바사아자차"
        self.assertAlmostEqual(production.narration_seconds(text), 3.3)
        self.assertAlmostEqual(production.narration_seconds("가 나\n다 라"), 3.18)
        cue = {"kind": "narration", "text": text, "duration": 75}
        self.assertEqual(len(production.narration_warnings([cue])), 1)
        self.assertEqual(production.narration_warnings([{**cue, "duration": 99}]), [])
        self.assertEqual(len(production.narration_warnings([{**cue, "duration": 2.5}], fps=1)), 1)
        self.assertEqual(production.caption_style_share({"captions": [{"kind": k} for k in ["narration"] * 2 + ["place"]]})["mood_share"], 1.0)

    def test_review_page_shows_caption_ratio(self):
        items = review.validate_candidates(candidates(), ENTRIES)
        with tempfile.TemporaryDirectory() as tmp:
            page = review.page_html("prod-x", 1, items, ENTRIES, Path(tmp))
        self.assertIn("자막 비율: 감성 1 · 예능 3 · 대사 0 (감성 25%, 목표 95% 참고 · 목표 범위 밖)", page)
        data = candidates()
        data["candidates"][0]["plan"]["captions"][0]["preset"] = "serif-fade"
        with self.assertRaisesRegex(ValueError, "c01: Caption preset"):
            review.validate_candidates(data, ENTRIES)


class FontLockTests(unittest.TestCase):
    def test_bundled_fonts_match_lock(self):
        doctor.verify_font_integrity(PROJECT_ROOT)
        lock = json.loads((PROJECT_ROOT / "config/fonts-lock.json").read_text())
        self.assertTrue(all(f["license"] == "SIL Open Font License 1.1" for f in lock["fonts"]))
        self.assertTrue(all(any(name.endswith("OFL.txt") for name in f["files"]) for f in lock["fonts"]))

    def test_tampered_or_extra_font_files_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            (root / "config").mkdir()
            shutil.copy2(PROJECT_ROOT / "config/fonts-lock.json", root / "config/fonts-lock.json")
            shutil.copytree(PROJECT_ROOT / "renderer/assets/fonts", root / "renderer/assets/fonts")
            doctor.verify_font_integrity(root)
            (root / "renderer/assets/fonts/jua/extra.ttf").write_text("unregistered")
            with self.assertRaises(ValueError):
                doctor.verify_font_integrity(root)
            (root / "renderer/assets/fonts/jua/extra.ttf").unlink()
            with (root / "renderer/assets/fonts/jua/Jua-Regular.ttf").open("ab") as font:
                font.write(b"x")
            with self.assertRaises(ValueError):
                doctor.verify_font_integrity(root)


@unittest.skipUnless(os.environ.get("VLOG_MEDIA_TESTS") == "1", "set VLOG_MEDIA_TESTS=1 (scripts/smoke-media.sh)")
class GalleryMediaTests(unittest.TestCase):
    def test_look_gallery_dimensions(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(os.path.realpath(tmp)) / "look-gallery.jpg"
            subprocess.run(["node", str(PROJECT_ROOT / "renderer/scripts/gallery.mjs"), str(output), "LookGallery"],
                           check=True, capture_output=True, text=True, timeout=300)
            probe = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(output)],
                                              check=True, capture_output=True, text=True).stdout)
            self.assertEqual((probe["streams"][0]["width"], probe["streams"][0]["height"]), (1920, 2160))

    def test_gallery_renders_every_preset(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(os.path.realpath(tmp)) / "gallery.jpg"
            subprocess.run(["node", str(PROJECT_ROOT / "renderer/scripts/gallery.mjs"), str(output)], check=True,
                           capture_output=True, text=True, timeout=300)
            probe = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(output)],
                                              check=True, capture_output=True, text=True).stdout)
            count = sum(len(spec["presets"]) for spec in REGISTRY["kinds"].values())
            self.assertEqual((probe["streams"][0]["width"], probe["streams"][0]["height"]), (1920, -(-count // 2) * 540))


if __name__ == "__main__":
    unittest.main()

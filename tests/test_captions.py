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
        self.assertEqual(REGISTRY["target_mood_share"], 0.9)
        self.assertNotIn("target_variety_share", REGISTRY)

    def test_caption_text_rules(self):
        self.assertEqual(production.validate_caption_text({"kind": "sfx_text", "text": "쾅"}, require_preset=False), "tilt-red")
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

    def test_review_page_shows_caption_ratio(self):
        items = review.validate_candidates(candidates(), ENTRIES)
        with tempfile.TemporaryDirectory() as tmp:
            page = review.page_html("prod-x", 1, items, ENTRIES, Path(tmp))
        self.assertIn("자막 비율: 감성 1 · 예능 3 · 대사 0 (감성 25%, 목표 90% 참고 · 목표 범위 밖)", page)
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

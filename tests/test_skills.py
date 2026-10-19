"""Project Skills: frontmatter, lock registration and references that must keep matching the code."""
import json
from pathlib import Path
import re
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
import production

CUSTOM = ["vlog-workflow", "vlog-scout", "k-variety-caption", "vlog-sound"]


def frontmatter(name):
    text = (PROJECT_ROOT / ".claude/skills" / name / "SKILL.md").read_text(encoding="utf-8")
    head, body = text.split("---\n", 2)[1:]
    return dict(re.findall(r"^([a-z-]+): (.+)$", head, re.M)), body


class SkillTests(unittest.TestCase):
    def test_frontmatter(self):
        for name in CUSTOM:
            with self.subTest(name=name):
                meta, body = frontmatter(name)
                self.assertEqual(meta["name"], name)
                self.assertGreater(len(meta["description"]), 40)
                self.assertTrue(body.strip())
        self.assertEqual(frontmatter("vlog-workflow")[0].get("disable-model-invocation"), "true")
        for name in CUSTOM[1:]:
            self.assertNotIn("disable-model-invocation", frontmatter(name)[0])

    def test_custom_skills_are_locked(self):
        lock = json.loads((PROJECT_ROOT / "config/skills-lock.json").read_text())
        custom = {s["name"]: s for s in lock["skills"] if s["scope"] == "project-custom"}
        self.assertEqual(sorted(custom), sorted(CUSTOM))
        upstream = [s for s in lock["skills"] if s["scope"] == "project"]
        self.assertEqual([s["name"] for s in upstream], ["remotion-best-practices"])

    def test_referenced_files_and_commands_exist(self):
        for name in CUSTOM:
            body = frontmatter(name)[1]
            for link in re.findall(r"\]\((\.\./[^)#]+)", body):
                with self.subTest(name=name, link=link):
                    self.assertTrue((PROJECT_ROOT / ".claude/skills" / name / link).resolve().is_file())
            for script in re.findall(r"python3 (scripts/[a-z_]+\.py)", body):
                with self.subTest(name=name, script=script):
                    self.assertTrue((PROJECT_ROOT / script).is_file())

    def test_scout_example_uses_registered_caption_kinds(self):
        body = frontmatter("vlog-scout")[1]
        example = json.loads(body.split("```json\n", 1)[1].split("```", 1)[0])
        for caption in example["candidates"][0]["plan"]["captions"]:
            production.validate_caption_text(caption, require_preset=False)

    def test_caption_skill_limits_match_registry(self):
        body = frontmatter("k-variety-caption")[1]
        registry = production.CAPTION_REGISTRY["kinds"]
        self.assertIn(f"받아치기 {registry['variety']['max_chars']}자", body)
        self.assertIn(f"효과 글자 {registry['sfx_text']['max_chars']}자", body)


if __name__ == "__main__":
    unittest.main()

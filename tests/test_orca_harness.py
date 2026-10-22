"""The Orca development flow must keep production single-agent and media out of worktrees."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "scripts"))
import dev_tests

MEDIA = ["sources/", "work/", "raw/", "assets/audio/", ".env"]
TEMPLATES = ["plan-worker.md", "coding-worker.md", "review-worker.md", "coordinator-takeover.md"]


def text(relative):
    return (PROJECT / relative).read_text()


class OrcaHarnessTests(unittest.TestCase):
    def test_agents_md_forbids_media_push_and_state_edits(self):
        agents = text("AGENTS.md")
        for path in MEDIA:
            self.assertIn(path, agents)
        for rule in ["Never push", "merge into `main`", "feature_list.json", "Never weaken tests", "./scripts/dev-check.sh"]:
            self.assertIn(rule, agents)

    def test_production_stays_single_agent(self):
        self.assertIn("no Codex handoff, external coordinator or subagent", text("CLAUDE.md"))
        self.assertIn("production 흐름에서는 subagent나 외부 coordinator를 쓰지 않습니다", text("docs/workflow.md"))
        for name in ["setup.example.json", "production.example.json"]:
            self.assertIs(json.loads(text(f"config/{name}"))["use_subagents"], False)

    def test_orca_sessions_pick_role_from_task_only_prompt(self):
        claude = text("CLAUDE.md")
        for rule in ["## Orca Development Sessions", "Dispatched worker", "caller.orcaSessionId",
                     "never coordinate", "The user's two approvals (plan, merge) still apply"]:
            self.assertIn(rule, claude)
        self.assertLess(claude.index("Dispatched worker"), claude.index("Orca coordinator"))
        self.assertIn("작업 내용만", text("docs/orca.md"))

    def test_worker_templates_forbid_media(self):
        for name in TEMPLATES:
            template = text(f"docs/orca/{name}")
            for path in MEDIA:
                self.assertIn(path, template, name)

    def test_orca_yaml_shares_only_toolchain(self):
        lines = [line.strip() for line in text("orca.yaml").splitlines()]
        shared = [line[2:] for line in lines if line.startswith("- ")]
        self.assertEqual(shared, [".tools", "renderer/node_modules"])
        self.assertIn("sharedDirectories:", lines)
        self.assertFalse(any(line.startswith("setup:") for line in lines))

    def test_dev_tests_skip_only_live_config_check(self):
        self.assertEqual(dev_tests.EXCLUDED, {"test_phase_configs.LiveConfigTests.test_live_config_is_valid_for_its_phase"})
        ids = {t.id() for t in dev_tests.flatten(dev_tests.dev_suite())}
        self.assertNotIn(next(iter(dev_tests.EXCLUDED)), ids)
        self.assertIn("test_phase_configs.LiveConfigTests.test_setup_example_is_the_setup_contract", ids)
        self.assertIn("test_orca_harness.OrcaHarnessTests.test_dev_tests_skip_only_live_config_check", ids)

    def test_run_state_is_ignored(self):
        self.assertIn(".orca-runs/", text(".gitignore").splitlines())

    def test_shared_symlinks_are_ignored(self):
        # Orca shares these as symlinks; a trailing-slash pattern would only match real directories.
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            shutil.copy(PROJECT / ".gitignore", root / ".gitignore")
            (root / "target").mkdir()
            (root / "renderer").mkdir()
            for link in [".tools", "renderer/node_modules"]:
                (root / link).symlink_to(root / "target")
            (root / "renderer/keep.txt").write_text("tracked sibling")
            status = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=root, check=True,
                                    capture_output=True, text=True).stdout
            self.assertNotIn(".tools", status)
            self.assertNotIn("node_modules", status)

    def test_docs_use_orca_branch_names(self):
        for path in ["AGENTS.md", "docs/orca.md", *[f"docs/orca/{name}" for name in TEMPLATES]]:
            self.assertNotIn("orca/<task>", text(path), path)
        self.assertIn("<git user>/<name>", text("AGENTS.md"))


if __name__ == "__main__":
    unittest.main()

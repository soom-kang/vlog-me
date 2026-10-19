"""Recovery regressions use text fixtures, never media tools or providers."""
import copy
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
import common
import inventory
import synthetic


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="vlog-recovery-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.config = common.read_json(PROJECT_ROOT / "config/setup.example.json")
        (self.root / "config").mkdir()
        common.write_json(self.root / "config/project.json", self.config)
        for module in (common, synthetic):
            root_patch = patch.object(module, "ROOT", self.root)
            root_patch.start()
            self.addCleanup(root_patch.stop)

    def make_run(self, succeeded=False):
        run = self.root / "work/synthetic-recovery"
        (run / "assets").mkdir(parents=True)
        manifest = {"owner": common.OWNER, "assets": {}}
        for name, kind, frames in [
            ("video", "video", 60), ("photo", "image", None),
            ("bgm", "audio", 120), ("sfx", "audio", 15),
        ]:
            source = run / "assets" / (name + ".txt")
            source.write_text("Synthetic state-test placeholder", encoding="utf-8")
            asset = {"file": source.name, "kind": kind, "sha256": common.digest(source)}
            if frames is not None:
                asset["frames"] = frames
            manifest["assets"][name] = asset
        timeline = {
            "schema_version": 1, "purpose": "synthetic_setup", "fps": 30,
            "width": 1280, "height": 720, "duration_frames": 120,
            "clips": [
                {"id": "video", "asset": "video", "from": 0, "duration": 60},
                {"id": "photo", "asset": "photo", "from": 60, "duration": 60},
            ],
            "audio": [{"id": "original", "asset": "video", "audio_track": 1,
                       "from": 0, "duration": 60, "gain_db": [[0, -6], [59, -6]]}],
            "captions": [],
        }
        common.write_json(run / "fixture-manifest.json", manifest)
        common.write_json(run / "timeline.json", timeline)
        common.write_json(run / "brief.json", {
            "purpose": "synthetic_setup", "source_roots": [],
            "resolved_config": copy.deepcopy(self.config),
        })
        state = {
            "owner": common.OWNER, "run_id": run.name, "stage": "prepared",
            "status": "pending", "input_fingerprint": common.input_fingerprint(run),
        }
        if succeeded:
            state.update(status="succeeded", stage="synthetic_encoded_output")
            names = ["preview.mp4", "frame.png", "verify.json", "audio-credits.md"]
            for name in names:
                (run / name).write_text("Synthetic output-test placeholder", encoding="utf-8")
            state["outputs"] = {name: common.digest(run / name) for name in names}
        common.write_json(run / "state.json", state)
        return run

    @staticmethod
    def fake_generation(command, **_kwargs):
        if command[0] != "ffmpeg":
            raise AssertionError(f"Unexpected command: {command[0]}")
        Path(command[-1]).write_text("Generated text fixture", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "", "")

    def test_new_defaults_do_not_invalidate_completed_run(self):
        run = self.make_run(succeeded=True)
        original_state = (run / "state.json").read_bytes()
        original_brief = (run / "brief.json").read_bytes()
        updated = copy.deepcopy(self.config)
        updated["editorial_direction"] = "Apply only to new runs"
        updated["synthetic_profile"]["concurrency"] = 1
        updated["synthetic_profile"]["timeout_seconds"] = 60
        common.write_json(self.root / "config/project.json", updated, replace=True)
        with patch.object(synthetic, "run_command", side_effect=AssertionError("Must reuse output")):
            self.assertEqual(synthetic.status(run.name)["status"], "succeeded")
            reused = synthetic.render(run.name)
        self.assertEqual(reused["status"], "succeeded")
        self.assertEqual((run / "state.json").read_bytes(), original_state)
        self.assertEqual((run / "brief.json").read_bytes(), original_brief)
        for name, expected in reused["outputs"].items():
            self.assertEqual(common.digest(run / name), expected)

    def test_generation_failure_is_readable_without_manifest(self):
        def fail_generation(command, **_kwargs):
            self.fake_generation(command)
            raise RuntimeError("Simulated ffmpeg failure")

        with patch.object(synthetic, "run_command", side_effect=fail_generation):
            with self.assertRaisesRegex(RuntimeError, "ffmpeg failure"):
                synthetic.create(2)
        run = next((self.root / "work").iterdir())
        self.assertFalse((run / "fixture-manifest.json").exists())
        state_before = (run / "state.json").read_bytes()
        state = synthetic.status(run.name)
        self.assertEqual(state["status"], "failed")
        self.assertEqual(state["stage"], "fixture_generation")
        self.assertIn("ffmpeg failure", state["error"])
        self.assertTrue((run / "assets/video.mp4").is_file())
        self.assertFalse((run / ".lock").exists())
        self.assertEqual((run / "state.json").read_bytes(), state_before)

    def test_inventory_failure_records_failed_preparation(self):
        with patch.object(synthetic, "run_command", side_effect=self.fake_generation), \
                patch.object(inventory, "run_command", side_effect=RuntimeError("Simulated ffprobe failure")):
            with self.assertRaisesRegex(RuntimeError, "ffprobe failure"):
                synthetic.create(2)
        run = next((self.root / "work").iterdir())
        state = synthetic.status(run.name)
        self.assertEqual(state["status"], "failed")
        self.assertIn("ffprobe failure", state["error"])
        self.assertTrue((run / "fixture-manifest.json").is_file())
        self.assertTrue((run / "timeline.json").is_file())
        self.assertFalse((run / "inventory.json").exists())
        self.assertFalse((run / ".lock").exists())
        self.assertEqual(common.read_json(run / "brief.json")["resolved_config"], self.config)

    def test_late_credit_collision_preserves_existing_content(self):
        run = self.make_run()
        user_credit = "User-owned credit created while renderer was running"

        def fake_render(command, **_kwargs):
            if command[0] == "node":
                (run / "preview.partial.mp4").write_text("Synthetic encoded-output placeholder")
                (run / "audio-credits.md").write_text(user_credit)
                return subprocess.CompletedProcess(command, 0, "{}", "")
            if command[0] == "ffprobe":
                probe = {"streams": [
                    {"codec_type": "video", "width": 1280, "height": 720, "codec_name": "h264"},
                    {"codec_type": "audio", "codec_name": "aac"},
                ], "format": {"duration": "4"}}
                return subprocess.CompletedProcess(command, 0, json.dumps(probe), "")
            if command[0] == "ffmpeg":
                if "-frames:v" in command:
                    Path(command[-1]).write_text("Synthetic frame placeholder")
                return subprocess.CompletedProcess(command, 0, "", '{"input_i":"-20", "input_tp":"-4"}')
            raise AssertionError(f"Unexpected command: {command[0]}")

        with patch.object(synthetic, "run_command", side_effect=fake_render):
            with self.assertRaises(FileExistsError):
                synthetic.render(run.name)
        self.assertEqual((run / "audio-credits.md").read_text(), user_credit)
        self.assertEqual(synthetic.status(run.name)["status"], "failed")
        self.assertTrue((run / "preview.mp4").exists())
        self.assertFalse((run / "verify.json").exists())
        self.assertFalse((run / ".lock").exists())

    def test_wrong_state_run_id_is_rejected_without_rewrite(self):
        run = self.make_run(succeeded=True)
        state = common.read_json(run / "state.json")
        state["run_id"] = "synthetic-another-run"
        common.write_json(run / "state.json", state, replace=True)
        saved = (run / "state.json").read_bytes()
        for action in (synthetic.status, synthetic.render):
            with self.subTest(action=action.__name__):
                with patch.object(synthetic, "run_command", side_effect=AssertionError("No commands allowed")):
                    with self.assertRaisesRegex(ValueError, "run ID mismatch"):
                        action(run.name)
                self.assertEqual((run / "state.json").read_bytes(), saved)
                self.assertFalse((run / ".lock").exists())

    def test_current_scope_blocks_create_before_allocating_run(self):
        for change in [{"phase": "production"}, {"external_processing": True},
                       {"source_roots": ["forbidden-source-root"]}]:
            with self.subTest(change=change):
                config = copy.deepcopy(self.config)
                config.update(change)
                common.write_json(self.root / "config/project.json", config, replace=True)
                with patch.object(synthetic, "run_command", side_effect=AssertionError("No commands allowed")):
                    with self.assertRaises(ValueError):
                        synthetic.create(2)
                self.assertFalse((self.root / "work").exists())

    def test_current_scope_blocks_reuse_even_when_frozen_config_is_valid(self):
        run = self.make_run(succeeded=True)
        saved = (run / "state.json").read_bytes()
        config = copy.deepcopy(self.config)
        config["audio_downloads"] = True
        common.write_json(self.root / "config/project.json", config, replace=True)
        with patch.object(synthetic, "run_command", side_effect=AssertionError("No commands allowed")):
            with self.assertRaises(ValueError):
                synthetic.render(run.name)
        self.assertEqual((run / "state.json").read_bytes(), saved)
        self.assertFalse((run / ".lock").exists())

    def test_scope_change_during_preparation_records_failure(self):
        def revoke_scope_during_inventory(_run_id):
            config = copy.deepcopy(self.config)
            config["phase"] = "production"
            common.write_json(self.root / "config/project.json", config, replace=True)
            return {"purpose": "synthetic_setup", "sources": []}

        with patch.object(synthetic, "run_command", side_effect=self.fake_generation), \
                patch.object(synthetic, "collect", side_effect=revoke_scope_during_inventory):
            with self.assertRaisesRegex(ValueError, "synthetic setup scope"):
                synthetic.create(2)
        run = next((self.root / "work").iterdir())
        state = synthetic.status(run.name)
        self.assertEqual(state["status"], "failed")
        self.assertEqual(state["stage"], "fixture_generation")
        self.assertIn("synthetic setup scope", state["error"])
        self.assertTrue((run / "inventory.json").is_file())
        self.assertEqual(common.read_json(run / "brief.json")["resolved_config"], self.config)
        self.assertFalse((run / ".lock").exists())

    def test_scope_change_during_render_retains_uncommitted_partial(self):
        run = self.make_run()
        fingerprint = common.input_fingerprint(run)
        partial_content = "Synthetic partial retained after scope change"

        def fake_render_with_scope_change(command, **_kwargs):
            if command[0] == "node":
                (run / "preview.partial.mp4").write_text(partial_content)
                config = copy.deepcopy(self.config)
                config["phase"] = "production"
                common.write_json(self.root / "config/project.json", config, replace=True)
                return subprocess.CompletedProcess(command, 0, "{}", "")
            if command[0] == "ffprobe":
                probe = {"streams": [
                    {"codec_type": "video", "width": 1280, "height": 720, "codec_name": "h264"},
                    {"codec_type": "audio", "codec_name": "aac"},
                ], "format": {"duration": "4"}}
                return subprocess.CompletedProcess(command, 0, json.dumps(probe), "")
            if command[0] == "ffmpeg":
                self.assertNotIn("-frames:v", command, "Must stop before final output extraction")
                return subprocess.CompletedProcess(command, 0, "", '{"input_i":"-20", "input_tp":"-4"}')
            raise AssertionError(f"Unexpected command: {command[0]}")

        with patch.object(synthetic, "run_command", side_effect=fake_render_with_scope_change):
            with self.assertRaisesRegex(ValueError, "synthetic setup scope"):
                synthetic.render(run.name)
        self.assertEqual(common.input_fingerprint(run), fingerprint)
        state = synthetic.status(run.name)
        self.assertEqual(state["status"], "failed")
        self.assertIn("synthetic setup scope", state["error"])
        self.assertEqual((run / "preview.partial.mp4").read_text(), partial_content)
        for name in ("preview.mp4", "verify.json", "frame.png", "audio-credits.md", ".lock"):
            self.assertFalse((run / name).exists(), name)

    @unittest.skipUnless(os.name == "posix", "Process-group cleanup requires POSIX signals")
    def test_sigint_stops_owned_child_before_releasing_lock(self):
        pid_file = self.root / "child.pid"
        child_code = (
            "import os,time; from pathlib import Path; "
            f"Path({str(pid_file)!r}).write_text(str(os.getpid())); time.sleep(30)"
        )
        parent_code = (
            "import sys; from pathlib import Path\n"
            f"sys.path.insert(0, {str(PROJECT_ROOT / 'scripts')!r})\n"
            "from common import run_command, run_lock\n"
            "try:\n"
            f" with run_lock(Path({str(self.root)!r})):\n"
            f"  run_command([sys.executable, '-B', '-c', {child_code!r}])\n"
            "except KeyboardInterrupt:\n"
            " raise SystemExit(130)\n"
        )
        parent = subprocess.Popen(
            [sys.executable, "-B", "-c", parent_code], stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        child_pid = None
        try:
            deadline = time.monotonic() + 5
            while not pid_file.exists() and parent.poll() is None and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue(pid_file.exists(), "Owned child did not start")
            child_pid = int(pid_file.read_text())
            self.assertTrue((self.root / ".lock").exists())
            parent.send_signal(signal.SIGINT)
            _, stderr = parent.communicate(timeout=8)
            self.assertEqual(parent.returncode, 130, stderr)
            with self.assertRaises(ProcessLookupError):
                os.kill(child_pid, 0)
            self.assertFalse((self.root / ".lock").exists())
        finally:
            if parent.poll() is None:
                parent.kill()
            parent.communicate(timeout=3)
            if child_pid is not None:
                try:
                    os.killpg(child_pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass


if __name__ == "__main__":
    unittest.main()

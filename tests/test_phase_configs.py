"""The harness must check itself in either phase. Tests read config/setup.example.json, never the live config."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
sys.path.insert(0, str(PROJECT_ROOT / "tests"))
import common
import doctor
import production
from test_production import production_config

SETUP = json.loads((PROJECT_ROOT / "config/setup.example.json").read_text())


class LiveConfigTests(unittest.TestCase):
    def test_live_config_is_valid_for_its_phase(self):
        live = json.loads((PROJECT_ROOT / "config/project.json").read_text())
        self.assertIn(live["phase"], {"setup_synthetic_only", "production"})
        if live["phase"] == "production":
            production.validate_production_config(live)
        else:
            common.validate_setup_config(live)

    def test_setup_example_is_the_setup_contract(self):
        common.validate_setup_config(SETUP)
        with self.assertRaises(ValueError):
            production.validate_production_config(SETUP)

    def test_tests_do_not_read_live_user_state(self):
        for path in (PROJECT_ROOT / "tests").glob("test_*.py"):
            if path.name == Path(__file__).name:
                continue
            text = path.read_text(encoding="utf-8")
            with self.subTest(test=path.name):
                self.assertNotRegex(text, r"(PROJECT_ROOT|parents\[1\]) / ['\"]config/(project|media-licenses)\.json")


class DoctorPhaseTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="vlog-doctor-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        (self.root / "config").mkdir()
        (self.root / "sources/trip").mkdir(parents=True)
        for name in ["toolchain.json", "media-licenses.json"]:
            shutil.copy2(PROJECT_ROOT / "config" / name, self.root / "config" / name)
        library = json.loads((self.root / "config/media-licenses.json").read_text())
        library["assets"] = []
        (self.root / "config/media-licenses.json").write_text(json.dumps(library))
        for module in (common, production):
            root_patch = patch.object(module, "ROOT", self.root)
            root_patch.start()
            self.addCleanup(root_patch.stop)

    def write(self, config):
        path = self.root / "config/project.json"
        common.write_json(path, config, replace=path.exists())

    def test_scope_passes_in_both_phases_and_rejects_mixtures(self):
        self.write(SETUP)
        self.assertEqual(doctor.scope_status(self.root)[0], "setup_synthetic_only")
        self.write(production_config())
        self.assertEqual(doctor.scope_status(self.root)[0], "production")
        self.write(production_config() | {"upload": True})
        with self.assertRaises(ValueError):
            doctor.scope_status(self.root)
        self.write(SETUP | {"source_roots": ["sources/trip"]})
        with self.assertRaises(ValueError):
            doctor.scope_status(self.root)

    def test_asr_status(self):
        self.assertEqual(doctor.asr_status(self.root, {"asr_model": None}), ("PASS", "NOT_CONFIGURED"))
        config = {"asr_model": "ggml-large-v3-turbo.bin"}
        with patch.object(doctor.shutil, "which", return_value="/opt/homebrew/bin/whisper-cli"):
            self.assertEqual(doctor.asr_status(self.root, config)[0], "FAIL")
            (self.root / ".tools/whisper").mkdir(parents=True)
            (self.root / ".tools/whisper/ggml-large-v3-turbo.bin").write_text("too small")
            self.assertIn("MODEL_SIZE_MISMATCH", doctor.asr_status(self.root, config)[1])
        with patch.object(doctor.shutil, "which", return_value=None):
            self.assertIn("NO_ENGINE", doctor.asr_status(self.root, config)[1])

    def test_audio_status(self):
        self.assertEqual(doctor.audio_status(self.root, {}), "EMPTY")


if __name__ == "__main__":
    unittest.main()

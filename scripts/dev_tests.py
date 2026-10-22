"""Run the unit tests a development worktree can pass.

Orca worktrees have no original media, so the one test that validates the live
production config against its source roots is left to ./init.sh in the main checkout.
"""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {"test_phase_configs.LiveConfigTests.test_live_config_is_valid_for_its_phase"}


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


def dev_suite(root=ROOT):
    loaded = unittest.defaultTestLoader.discover(str(root / "tests"), top_level_dir=str(root / "tests"))
    return unittest.TestSuite(t for t in flatten(loaded) if t.id() not in EXCLUDED)


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=1).run(dev_suite())
    sys.exit(0 if result.wasSuccessful() else 1)

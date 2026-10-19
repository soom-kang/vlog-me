#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from common import ROOT, validate_run, require_setup_scope

parser = argparse.ArgumentParser(description="Validate synthetic setup inputs; production sources are disabled.")
choice = parser.add_mutually_exclusive_group(required=True)
choice.add_argument("--run-id")
choice.add_argument("--fixtures", action="store_true")
parser.add_argument("--for-render", action="store_true", help="Check current setup scope before a write operation")
args = parser.parse_args()
if args.fixtures:
    raise SystemExit(subprocess.call([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=ROOT))
try:
    if args.for_render:
        require_setup_scope()
    _, _, timeline = validate_run(args.run_id)
    print(json.dumps({"status": "PASS", "run_id": args.run_id, "duration_frames": timeline["duration_frames"]}))
except (ValueError, OSError, KeyError, TypeError) as exc:
    parser.exit(1, f"FAIL: {exc}\n")

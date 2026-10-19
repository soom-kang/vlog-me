#!/usr/bin/env python3
"""Inspect only registered, hash-checked synthetic setup assets."""
import argparse
import json
from common import check_assets, require_run, run_command, safe_path


def collect(run_id):
    run, manifest = require_run(run_id)
    check_assets(run, manifest)
    records = []
    for source_id, asset in manifest["assets"].items():
        path = safe_path(run / "assets", asset["file"], exists=True)
        metadata = json.loads(run_command(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)]).stdout)
        records.append({"source_id": source_id, "kind": asset["kind"], "sha256": asset["sha256"], "metadata": metadata})
    return {"purpose": "synthetic_setup", "sources": records, "content_review": "not_performed"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(collect(args.run_id), indent=2))
    except (ValueError, OSError, RuntimeError) as exc:
        parser.exit(1, f"FAIL: {exc}\n")

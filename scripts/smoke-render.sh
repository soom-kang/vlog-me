#!/bin/bash
set -euo pipefail
source "$(dirname "$0")/env.sh"
cd "$VLOG_ROOT"
phase=$(python3 -c 'import json; print(json.load(open("config/project.json"))["phase"])')
if [ "$phase" != "setup_synthetic_only" ]; then
  echo "SKIP: synthetic smoke renders run only in the setup phase (current: $phase)." >&2
  echo "In production use ./scripts/smoke-media.sh and ./scripts/smoke-longform.sh (temporary roots), or restore config/setup.example.json first." >&2
  exit 3
fi
exec python3 scripts/synthetic.py smoke "$@"

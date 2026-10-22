#!/bin/bash
# Development checks for Orca worktrees, which have no original media. ./init.sh stays the full check.
set -euo pipefail
source "$(dirname "$0")/env.sh"
cd "$VLOG_ROOT"
python3 scripts/dev_tests.py
python3 -m compileall -q scripts tests
npm --prefix renderer run lint
npm --prefix renderer run typecheck
npm --prefix renderer test
echo 'PASS: dev tests, lint, typecheck and renderer tests. Run ./init.sh in the main checkout after merge.'

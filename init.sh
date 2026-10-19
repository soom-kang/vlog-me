#!/bin/bash
set -euo pipefail
source "$(dirname "$0")/scripts/env.sh"
cd "$VLOG_ROOT"
./scripts/doctor.sh
python3 -m unittest discover -s tests -v
python3 -m compileall -q scripts tests
npm --prefix renderer run lint
npm --prefix renderer run typecheck
npm --prefix renderer test
echo 'PASS: local preflight, contracts, lint, typecheck and tests. Render/model checks are separate.'

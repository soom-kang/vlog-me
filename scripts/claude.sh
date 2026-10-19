#!/bin/bash
set -euo pipefail
source "$(dirname "$0")/env.sh"
cd "$VLOG_ROOT"
exec claude "$@"

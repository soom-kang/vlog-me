#!/bin/bash
# Source this from project entrypoints; do not modify the user's shell profile.
VLOG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -d /opt/homebrew/bin ]; then
  export PATH="/opt/homebrew/bin:$PATH"
fi
VLOG_LOCAL_NODE="$VLOG_ROOT/.tools/node-v24.22.0-darwin-arm64/bin"
if [ -x "$VLOG_LOCAL_NODE/node" ]; then
  export PATH="$VLOG_LOCAL_NODE:$PATH"
fi
export npm_config_cache="$VLOG_ROOT/.cache/npm"
export npm_config_update_notifier=false
export npm_config_fund=false
export npm_config_audit=false

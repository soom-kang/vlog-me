#!/bin/bash
# Build a 2-minute synthetic edit end to end (ingest → analyze → review → select → assemble → chunked render)
# in a temporary root and measure frames, loudness and A/V sync. Takes several minutes; never reads real originals.
set -euo pipefail
source "$(dirname "$0")/env.sh"
cd "$VLOG_ROOT"
VLOG_MEDIA_TESTS=1 exec python3 -m unittest tests.test_longform.LongformMediaTests -v

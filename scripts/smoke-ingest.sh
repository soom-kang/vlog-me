#!/bin/bash
# Generate synthetic HDR/VFR/rotated/silent clips and HEIC photos in a temporary root and ingest them.
# Never reads real originals; the project's own config and work/ are untouched.
set -euo pipefail
source "$(dirname "$0")/env.sh"
cd "$VLOG_ROOT"
VLOG_MEDIA_TESTS=1 exec python3 -m unittest tests.test_ingest.IngestMediaTests -v

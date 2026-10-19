#!/bin/bash
# Generate synthetic HDR/VFR/rotated/silent clips, a loud burst, Korean TTS speech and HEIC photos in a
# temporary root, then ingest, analyze and render review cards (needs localhost and the project browser). Never reads real originals; project config and work/ are untouched.
# Transcription runs when .tools/whisper/ggml-large-v3-turbo.bin exists (or VLOG_WHISPER_MODEL is set).
set -euo pipefail
source "$(dirname "$0")/env.sh"
cd "$VLOG_ROOT"
DEFAULT_MODEL="$VLOG_ROOT/.tools/whisper/ggml-large-v3-turbo.bin"
if [ -z "${VLOG_WHISPER_MODEL:-}" ] && [ -f "$DEFAULT_MODEL" ]; then
  export VLOG_WHISPER_MODEL="$DEFAULT_MODEL"
fi
VLOG_MEDIA_TESTS=1 exec python3 -m unittest tests.test_ingest.IngestMediaTests tests.test_analyze.AnalyzeMediaTests tests.test_review.ReviewMediaTests tests.test_captions.GalleryMediaTests tests.test_sound.SoundMediaTests -v

#!/usr/bin/env bash
# tools/run-review.sh — fire one reviewer; capture envelope + stderr.
#
# Thin composing wrapper around tools/run-with-model.sh. Refuses exit 2
# on missing/empty positional args; does NOT re-check $DROID_MODEL_ID
# (run-with-model.sh owns that gate — §17.1 single source of truth).
#
# Usage: DROID_MODEL_ID=<modelId> bash tools/run-review.sh <modelId> <prompt-file>
# Writes: ./review-<modelId>-envelope.json + ./review-<modelId>-stderr.log
# Exit:   0 on success; 2 on bad args (mirrors run-with-model.sh exit 2).
set -euo pipefail
if [ "$#" -ne 2 ] || [ -z "$1" ] || [ -z "$2" ]; then
  echo "run-review.sh: expected 2 non-empty args (<modelId> <prompt-file>)" >&2
  exit 2
fi
MODEL="$1"; PROMPT="$2"
DROID_MODEL_ID="$MODEL" bash tools/run-with-model.sh \
  droid exec --model "$MODEL" -f "$PROMPT" --auto medium --cwd "$PWD" --output-format json \
    > "review-${MODEL}-envelope.json" 2> "review-${MODEL}-stderr.log"

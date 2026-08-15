#!/usr/bin/env bash
# tools/run-review.sh — fire one reviewer; steer envelope + stderr
# to a sprint-keyed canonical directory (NOT cwd, NOT phase-4.5).
#
# Composing wrapper around tools/run-with-model.sh. Refuses:
#   exit 2 — missing or empty positional args
#   exit 3 — sprint-keyed canonical dir cannot be created (mkdir -p fail)
#
# Self-anchored via ${BASH_SOURCE[0]} (chunk-D5-1a) so callers can
# run this script from any cwd.
#
# Usage: DROID_MODEL_ID=<modelId> bash tools/run-review.sh \
#        <modelId> <prompt-file> <sprint-name>
# Writes: ${REPO}/evidence/reviews/<sprint-name>/round{N}/\
#         review-<modelId>-envelope.json + review-<modelId>-stderr.log
# Exit:   0 on success; 2 on bad args; 3 on mkdir failure.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_WITH_MODEL="${SCRIPT_DIR}/run-with-model.sh"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
if [ "$#" -ne 3 ] || [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ]; then
  echo "run-review.sh: expected 3 non-empty args (<modelId> <prompt-file> <sprint-name>)" >&2
  exit 2
fi
MODEL="$1"; PROMPT="$2"; SPRINT="$3"
SPRINT_DIR="${REPO_ROOT}/evidence/reviews/${SPRINT}"
ROUND=1
for n in 1 2 3 4 5 6 7 8 9 10; do
  if [ ! -d "${SPRINT_DIR}/round${n}" ]; then ROUND="round${n}"; break; fi
done
mkdir -p "${SPRINT_DIR}/${ROUND}" || {
  echo "run-review.sh: could not mkdir '${SPRINT_DIR}/${ROUND}'" >&2
  exit 3
}
DROID_MODEL_ID="$MODEL" bash "$RUN_WITH_MODEL" \
  droid exec --model "$MODEL" -f "$PROMPT" --auto medium --cwd "$PWD" --output-format json \
    > "${SPRINT_DIR}/${ROUND}/review-${MODEL}-envelope.json" \
    2> "${SPRINT_DIR}/${ROUND}/review-${MODEL}-stderr.log"

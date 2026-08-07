#!/usr/bin/env bash
# tools/run-with-model.sh — refuse to run a droid exec unless $DROID_MODEL_ID is set.
#
# In line with PRD.md §17.1: every droid exec invocation must pass --model <modelId>.
# This wrapper is a cheap insurance layer for the foot-gun case where a runner
# forgets to write --model and falls back to --auto.
#
# Usage:
#   DROID_MODEL_ID=gpt-5.4-mini bash tools/run-with-model.sh \
#       droid exec --model "$DROID_MODEL_ID" \
#           -f <prompt> --auto low --cwd <path>
#
# Behaviour:
#   - If $DROID_MODEL_ID is unset or empty, exit 2 with a one-line rule reminder.
#   - Otherwise pass the command through verbatim. No transformation.
set -euo pipefail

if [ -z "${DROID_MODEL_ID:-}" ]; then
    cat >&2 <<'EOF'
run-with-model.sh: refusing to run. $DROID_MODEL_ID is unset.

Per PRD.md §17.1, every droid exec invocation must pass --model explicitly.
Set DROID_MODEL_ID=<modelId> (e.g., gpt-5.4-mini, gemini-2.5-pro, grok-4.5,
claude-opus-4-8) in the environment before invoking, and pass
--model "$DROID_MODEL_ID" to droid exec. See tools/conventions/commit-body-
recipe.md for the commit-body form of the chosen model.
EOF
    exit 2
fi

if [ "$#" -lt 1 ]; then
    echo "run-with-model.sh: expected at least one argument (the droid exec command)" >&2
    exit 2
fi

exec "$@"

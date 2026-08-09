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

# PRD §3.2 GO-NO-GO: droid exec --mission is a closed path. The Phase 0
# experiment showed Mission-native mode is a no-op that reports success
# (silent-green defect equivalent). Refuse it at the wrapper so neither a
# tired operator nor an automated runner can route through it silently.
# Escape the GO-NO-GO with DROID_ALLOW_MISSION=1 only for explicit re-probing
# — that override is logged by the caller and reviewed, not used casually.
for arg in "$@"; do
    if [ "$arg" = "--mission" ]; then
        if [ "${DROID_ALLOW_MISSION:-0}" = "1" ]; then
            echo "run-with-model.sh: WARNING --mission is being passed with DROID_ALLOW_MISSION=1" >&2
            echo "  (the GO-NO-GO closed this path; this is a re-probe, not casual use)" >&2
            break
        fi
        cat >&2 <<'EOF'
run-with-model.sh: refusing to run. --mission was passed.

Per PRD §3.2 GO-NO-GO, droid exec --mission is a closed path: Mission mode
is a no-op that reports success (silent-green defect). The framework is
command-orchestrated (tools/orchestrate-review.py + tools/sprint-loop.py).
If you are re-probing Mission-native and have an explicit path in
phase-N/KNOWN-ISSUES.md, set DROID_ALLOW_MISSION=1 and document the run.
EOF
        exit 3
    fi
done

exec "$@"

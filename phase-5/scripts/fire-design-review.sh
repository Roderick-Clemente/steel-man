#!/usr/bin/env bash
# Fire a cross-family design review for a documentation artifact.
#
# ── ACKNOWLEDGED DEBT ────────────────────────────────────────────────────────
# This script exists because tools/orchestrate-review.py has no path for
# reviewing a non-code artifact (it hard-requires --test-file/--lock-file/
# --pilot-python). Per OPERATING-RULES §18.4 that made it the wrong fix: the
# workaround now owns the debt. phase-5/TASK-DESIGN-REVIEW-PHASE.md D1 subsumes
# it, and the chunk that lands D1 DELETES this file. Do not grow it.
#
# ── SEAT ─────────────────────────────────────────────────────────────────────
# This is the ORCHESTRATOR seat (§24: fire XOR sign). It fires reviewers and
# never signs. Reviewer models are REQUIRED arguments, never defaulted, because
# §22.3 forbids the firing agent from selecting the seats it fires — that choice
# belongs to the operator. It refuses to run if a signing key is present in the
# environment, so a process that could sign cannot also fire.
#
# ── WHY THE FLAGS ARE WHAT THEY ARE ──────────────────────────────────────────
# --auto medium: run r-drs-role-split-1 burned a grok-4.5 call at droid's default
#   read-only tier. The CLI aborts the whole session when a reviewer needs a
#   command the tier refuses, rather than degrading. `Execute` in --enabled-tools
#   is necessary and NOT sufficient; the autonomy tier must also permit it.
# git worktree: medium autonomy can write, so the reviewer runs against a
#   detached worktree at a pinned sha. It cannot reach the artifact under review,
#   and any mutation it attempts is captured as evidence instead of silently
#   discarded.
# --output-format stream-json: kept deliberately, though adapters/factory.py
#   cannot yet parse JSONL (F-REF-005). stream-json carries per-event session_id
#   and terminal error events, which §23 operational-distinctness needs and
#   whole-file json does not expose. The adapter is the thing that should adapt;
#   Chunk D owns that call.
#
# Usage:
#   bash phase-5/scripts/fire-design-review.sh \
#       --artifact phase-5/DESIGN-ROLE-SPLIT-AND-SIGNALS.md \
#       --prompt   phase-5/prompts/design-review-role-split.md \
#       --models   grok-4.5,gpt-5.2 \
#       [--run-id r-drs-...] [--sha <commit>]
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

ARTIFACT=""; PROMPT=""; MODELS=""; RUN_ID=""; SHA=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        --artifact) ARTIFACT="$2"; shift 2 ;;
        --prompt)   PROMPT="$2";   shift 2 ;;
        --models)   MODELS="$2";   shift 2 ;;
        --run-id)   RUN_ID="$2";   shift 2 ;;
        --sha)      SHA="$2";      shift 2 ;;
        *) echo "unknown arg: $1" >&2; exit 2 ;;
    esac
done

die() { echo "fire-design-review: $*" >&2; exit 2; }

[ -n "$ARTIFACT" ] || die "--artifact is required"
[ -n "$PROMPT" ]   || die "--prompt is required"
[ -f "$PROMPT" ]   || die "--prompt not found: $PROMPT"
[ -f "$ARTIFACT" ] || die "--artifact not found: $ARTIFACT"
[ -n "$MODELS" ]   || die "--models is required and is never defaulted.
  §22.3: the firing seat must not select the reviewers it fires. Ask the
  operator for the seats. Legal non-Claude ids per MODEL_FAMILY_MAP:
  grok-4.5, gpt-5.2, gpt-5.4-mini, gemini-3.1-pro-preview, gemini-2.5-pro, glm-5.2"

# §24: a process that can sign must not fire.
for k in EVIDENCE_SIGNING_KEY EVIDENCE_SIGNING_KEY_REFEREE; do
    if [ -n "${!k:-}" ]; then
        die "refusing to fire: $k is set in this environment.
  Fire and sign must not share a process (§24). Unset it or fire from an
  orchestrator seat that never holds a signing key."
    fi
done

# Pin the artifact: a moving target makes round N and N+1 incomparable (F-REF-007).
if [ -z "$SHA" ]; then
    SHA="$(git rev-parse HEAD)"
fi
if ! git diff --quiet HEAD -- "$ARTIFACT"; then
    die "refusing to fire: $ARTIFACT is dirty relative to HEAD.
  Commit it first so the review pins identifiable bytes."
fi
ARTIFACT_SHA="$(git rev-parse "${SHA}:${ARTIFACT}")"

RUN_ID="${RUN_ID:-r-artifact-review-$(date +%s)}"
RUN_DIR="phase-4.5/build-evidence/${RUN_ID}"
ENV_DIR="${RUN_DIR}/envelopes"
[ -e "$RUN_DIR" ] && die "run dir already exists: $RUN_DIR (pick a fresh --run-id)"
mkdir -p "$ENV_DIR"

WT="$(mktemp -d "${TMPDIR:-/tmp}/adv-review-wt.XXXXXX")"
cleanup() {
    # Capture reviewer mutation as evidence BEFORE discarding the worktree.
    if [ -d "$WT/.git" ] || [ -f "$WT/.git" ]; then
        git -C "$WT" status --porcelain > "${RUN_DIR}/worktree-mutation.txt" 2>&1 || true
        if [ -s "${RUN_DIR}/worktree-mutation.txt" ]; then
            echo "NOTE: a reviewer mutated its worktree; evidence in ${RUN_DIR}/worktree-mutation.txt" >&2
            echo "  worktree preserved at $WT for inspection" >&2
            return
        fi
    fi
    git worktree remove --force "$WT" >/dev/null 2>&1 || rm -rf "$WT"
}
trap cleanup EXIT

git worktree add --detach "$WT" "$SHA" >/dev/null

{
    echo "run_id:        $RUN_ID"
    echo "artifact:      $ARTIFACT"
    echo "artifact_blob: $ARTIFACT_SHA"
    echo "commit:        $SHA"
    echo "branch:        $(git rev-parse --abbrev-ref HEAD)"
    echo "prompt:        $PROMPT"
    echo "prompt_sha256: $(shasum -a 256 "$PROMPT" | cut -d' ' -f1)"
    echo "models:        $MODELS"
    echo "droid:         $(droid --version)"
    echo "worktree:      $WT (detached, reviewers cannot reach the primary tree)"
    echo "auto_level:    medium"
} | tee "${RUN_DIR}/provenance.txt"
echo

IFS=',' read -r -a REVIEWERS <<< "$MODELS"
[ "${#REVIEWERS[@]}" -ge 2 ] || die "need >=2 reviewer seats for §17.2 family distinctness"

pids=(); labels=()
for model in "${REVIEWERS[@]}"; do
    out="${ENV_DIR}/${model}.raw.txt"
    err="${ENV_DIR}/${model}.stderr.txt"
    echo "firing $model -> $out"
    DROID_MODEL_ID="$model" bash tools/run-with-model.sh \
        droid exec --model "$model" \
            --enabled-tools Read,Glob,Grep,LS,Execute \
            --auto medium \
            --output-format stream-json \
            --cwd "$WT" \
            -f "$PROMPT" \
        >"$out" 2>"$err" &
    pids+=("$!"); labels+=("$model")
done

for i in "${!pids[@]}"; do
    if wait "${pids[$i]}"; then
        echo "exit 0: ${labels[$i]}"
    else
        echo "exit $?: ${labels[$i]} (nonzero is NOT the verdict check; see below)" >&2
    fi
done

echo
echo "=== verdict-presence guard (§7: a digest is not a verdict) ==="
# This is the check that matters. It exits non-zero when any envelope carries no
# verdict, so a burned round cannot be reported as a completed review.
python3 phase-5/scripts/envelope-manifest.py "$RUN_DIR" \
    --json "${RUN_DIR}/manifest.json" \
    --markdown "${RUN_DIR}/manifest.md"

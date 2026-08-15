#!/usr/bin/env bash
# Regression-vs-rot evidence for chunk-D1-2a.
#
# The four repaired scripts were broken at chunk-D1-2's tip (ee90061). The
# question a reviewer should ask is whether chunk-2's directory move BROKE them
# or merely inherited something already broken — the fix is defensible either
# way, but only the first makes it a regression the layout refactor owes.
#
# Answered by running the same four scripts at the PREDECESSOR commit c63b776
# (the commit before the move) in a throwaway worktree, where they still sit at
# their pre-move paths. Nothing is measured against the live repo, and the
# worktree is removed at the end.
#
# rc is captured by redirecting to a file, never through a pipe.
#
# The @HEAD column snapshots and restores telemetry/runs.jsonl, for a reason
# worth recording: the first version of this harness probed @HEAD with
# `--dry-run`, assuming that was a safe read. It is not. Only
# reconstruct-telemetry.py parses arguments; both gen-telemetry.py scripts
# ignore argv entirely, so `--dry-run` is silently discarded and the script
# performs its real truncating write. A flag that is honoured by one script in a
# family and ignored by the rest is a silent-green shape (§7) — it was found by
# noticing the live row count had changed, not by any rc.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../../../.." && pwd)"
PY=/private/tmp/asprint-venv/bin/python
WT="$(mktemp -d)/pred-c63b776"
PRED=c63b776

SOR="$REPO/telemetry/runs.jsonl"
SNAP="$(mktemp)"
cp "$SOR" "$SNAP"
SNAP_SHA="$(shasum -a 256 "$SNAP" | awk '{print $1}')"

echo "predecessor: $PRED   (chunk-D1-2 tip for comparison: ee90061)"
echo "worktree:    $WT"
echo "SoR snapshot: $(grep -c . "$SNAP") rows, sha256 $SNAP_SHA"
( cd "$REPO" && git worktree add --detach "$WT" "$PRED" ) > /dev/null 2>&1 || {
  echo "FAILED to create the worktree"; exit 1; }
echo

# Pre-move paths, and the post-move path each one now lives at.
PRE=(
  "phase-3/gen-telemetry.py|tools/phase-3-gen/gen-telemetry.py"
  "phase-3.1/gen-telemetry.py|tools/phase-3.1-gen/gen-telemetry.py"
  "phase-4/reconstruct-telemetry.py|tools/phase-4-gen/reconstruct-telemetry.py"
  "phase-4/gen-findings.py|tools/phase-4-gen/gen-findings.py"
)

printf '%-38s %-9s %-9s %s\n' "script (pre-move path)" "@$PRED" "@HEAD" "verdict"
printf '%-38s %-9s %-9s %s\n' "--------------------------------------" "--------" "--------" "-------"
for pair in "${PRE[@]}"; do
  old="${pair%%|*}"; new="${pair##*|}"
  # Predecessor: run from the worktree root, the CWD these scripts assumed.
  ( cd "$WT" && "$PY" "$WT/$old" --dry-run ) > "$HERE/pred-$(basename "$(dirname "$old")")-$(basename "$old" .py).out" 2>&1
  rc_old=$?
  if [ $rc_old -ne 0 ]; then
    ( cd "$WT" && "$PY" "$WT/$old" ) > "$HERE/pred-$(basename "$(dirname "$old")")-$(basename "$old" .py).out" 2>&1
    rc_old=$?
  fi
  # Current tree, from a non-root CWD (the fix must be CWD-independent).
  ( cd /tmp && "$PY" "$REPO/$new" --dry-run ) > /dev/null 2>&1
  rc_new=$?
  if [ $rc_new -ne 0 ]; then ( cd /tmp && "$PY" "$REPO/$new" ) > /dev/null 2>&1; rc_new=$?; fi
  if [ $rc_old -eq 0 ]; then verdict="chunk-2 REGRESSION (worked pre-move)"; else verdict="pre-existing rot"; fi
  printf '%-38s rc=%-6d rc=%-6d %s\n' "$old" "$rc_old" "$rc_new" "$verdict"
done
echo
echo "Note: the SoR-shrink property of phase-3/gen-telemetry.py is also"
echo "pre-existing, and provable independently of rc — the full-file rewrite is"
echo "in the predecessor source, not introduced by this chunk:"
( cd "$WT" && grep -n 'open(OUT, "w")' phase-3/gen-telemetry.py | sed 's/^/  '"$PRED"':/' )
( cd "$REPO" && grep -n 'open(OUT, "w")' tools/phase-3-gen/gen-telemetry.py | sed 's/^/  HEAD:/' )
echo

( cd "$REPO" && git worktree remove --force "$WT" ) && echo "worktree removed."
( cd "$REPO" && git worktree prune )

cp "$SNAP" "$SOR"
RESTORED="$(shasum -a 256 "$SOR" | awk '{print $1}')"
echo "live SoR restored: $(grep -c . "$SOR") rows, sha $RESTORED"
[ "$RESTORED" = "$SNAP_SHA" ] && echo "  pass: byte-identical to the pre-run snapshot" || echo "  FAIL: SoR not restored"
rm -f "$SNAP"

#!/usr/bin/env bash
# chunk-D1-2a exit-criteria harness (CHUNK-2a-SPEC §4.1–§4.7).
#
# Why a script and not a transcript of shell one-liners (§9): §4.2 and §4.7
# require RUNNING the four repaired scripts, and three of them WRITE
# telemetry/runs.jsonl — the system of record. Two of those three
# (phase-3 / phase-3.1 generators) rewrite the whole file rather than append,
# which is pre-existing behaviour, not a chunk-2a regression: at predecessor
# c63b776 the same script already did `open(OUT, "w")` (see :104 there, :121
# here). So a naive "run all four in a row" measures the LAST script against a
# SoR the earlier ones already replaced, and would report a shrink that the
# path fix did not cause.
#
# This harness therefore snapshots the SoR, measures each script from the SAME
# baseline, and restores the snapshot at the end with a sha comparison. Every
# rc is captured by redirecting to a file — never through a pipe, because `$?`
# after a pipeline is the LAST command's status (that mistake is why chunk-D1-2
# briefly recorded a silent-green rc for local_backend.py).
#
# Usage: bash verify-chunk2a.sh   (from anywhere; paths are self-anchored)
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../../../.." && pwd)"
PY=/private/tmp/asprint-venv/bin/python
SOR="$REPO/telemetry/runs.jsonl"
WORK="$(mktemp -d)"
SNAP="$WORK/runs.jsonl.snapshot"

echo "repo:        $REPO"
echo "interpreter: $PY  ($($PY -V 2>&1))"
echo "scratch:     $WORK"
echo

cp "$SOR" "$SNAP"
SNAP_SHA="$(shasum -a 256 "$SNAP" | awk '{print $1}')"
BEFORE="$(grep -c . "$SNAP")"
echo "SoR snapshot: $BEFORE rows, sha256 $SNAP_SHA"
echo

echo "########## §4.1 — full suite on the suite interpreter ##########"
( cd "$REPO" && "$PY" -m pytest -p no:cacheprovider ) > "$HERE/suite.out" 2>&1
echo "rc=$?"
tail -3 "$HERE/suite.out"
echo

echo "########## §4.2 + §4.7 — the four scripts, from a NON-ROOT CWD ##########"
echo "each run starts from the same restored SoR baseline of $BEFORE rows"
echo
run_script() {
  local rel="$1"; shift
  local tag; tag="$(basename "$(dirname "$rel")")-$(basename "$rel" .py)$([ $# -gt 0 ] && echo "-dryrun")"
  cp "$SNAP" "$SOR"
  ( cd "$WORK" && "$PY" "$REPO/$rel" "$@" ) > "$HERE/run-$tag.out" 2> "$HERE/run-$tag.err"
  local rc=$?
  local after; after="$(grep -c . "$SOR")"
  local forked="no"; [ -e "$REPO/tools/telemetry" ] && forked="YES"
  printf '%-46s rc=%d  SoR %s->%s  tools/telemetry:%s\n' "$rel $*" "$rc" "$BEFORE" "$after" "$forked"
  # §4.7: the merge guard must SEE the existing rows. The judge's
  # `"0 existing rows" not in stdout` assertion cannot fire (the script prints
  # "Existing rows: N"), so assert on the real string here.
  grep -h '^Existing rows:' "$HERE/run-$tag.out" 2>/dev/null | sed 's/ (run_ids.*//' | sed 's/^/    /'
  head -2 "$HERE/run-$tag.out" | grep -v '^Existing rows:' | sed 's/^/    /'
  [ -s "$HERE/run-$tag.err" ] && { echo "    STDERR:"; sed 's/^/      /' "$HERE/run-$tag.err"; }
  return 0
}
run_script tools/phase-4-gen/reconstruct-telemetry.py --dry-run
run_script tools/phase-4-gen/gen-findings.py
run_script tools/phase-3-gen/gen-telemetry.py
run_script tools/phase-3.1-gen/gen-telemetry.py
run_script tools/phase-4-gen/reconstruct-telemetry.py
echo

echo "########## §4.7 — do the emitted envelope_paths resolve? ##########"
# Measured on the SoR left by the final (real) reconstruct run, partitioned:
# rows these four scripts generate vs rows that were already in the file.
( cd "$REPO" && "$PY" - <<'PYEOF'
import json, os, collections
GEN = {"phase-2", "phase-3", "phase-3.1"}
stats = collections.Counter(); unresolved = collections.defaultdict(list)
for line in open("telemetry/runs.jsonl"):
    line = line.strip()
    if not line:
        continue
    r = json.loads(line)
    grp = "script-generated" if r.get("phase") in GEN else "pre-existing row"
    p = r.get("envelope_path")
    ok = bool(p) and os.path.isfile(p)
    stats[(grp, "resolves" if ok else "UNRESOLVED")] += 1
    if not ok:
        unresolved[grp].append(p)
for (grp, verdict), n in sorted(stats.items()):
    print(f"  {grp:18s} {verdict:11s} {n}")
for grp, items in unresolved.items():
    print(f"  {grp}: {len(items)} unresolved, e.g. {items[0]!r}")
PYEOF
) 2>&1
echo

echo "########## §4.7 — forked telemetry tree ##########"
if [ -e "$REPO/tools/telemetry" ]; then echo "  FAIL: $REPO/tools/telemetry exists"; else echo "  pass: tools/telemetry absent on disk"; fi
( cd "$REPO" && git status --porcelain | grep -i 'tools/telemetry' ) && echo "  FAIL: porcelain hit" || echo "  pass: nothing under tools/telemetry in git status --porcelain"
echo

echo "########## restore the SoR ##########"
cp "$SNAP" "$SOR"
RESTORED="$(shasum -a 256 "$SOR" | awk '{print $1}')"
echo "  restored sha256 $RESTORED"
[ "$RESTORED" = "$SNAP_SHA" ] && echo "  pass: byte-identical to the pre-run snapshot" || echo "  FAIL: SoR not restored"
echo

echo "########## §4.3 — residual phase-[0-9] occurrences (listed, not hidden) ##########"
( cd "$REPO" && grep -rn 'phase-[0-9]' \
    tools/phase-3-gen/gen-telemetry.py \
    tools/phase-3.1-gen/gen-telemetry.py \
    tools/phase-4-gen/reconstruct-telemetry.py \
    tools/phase-4-gen/gen-findings.py \
    tools/phase-1-scripts/lock.py \
    tools/phase-1-hooks/locked-test-guard.py ) > "$HERE/residual-phase-literals.out" 2>&1
echo "  $(grep -c . "$HERE/residual-phase-literals.out") occurrences -> residual-phase-literals.out"
echo "  path-forming ones (bare 'phase-N/...' as a path literal): judged by"
echo "  test_chunk2a_no_stale_phase_prefix_literals, which is green in suite.out."
echo

echo "########## §4.4 — judges byte-unchanged and lock-matching ##########"
for f in tests/test_layout_paths.py tests/test_layout_paths_chunk2.py tests/test_layout_paths_chunk2a.py; do
  d="$(shasum -a 256 "$REPO/$f" | awk '{print $1}')"
  l="$("$PY" -c "import json;print(json.load(open('$REPO/tools/phase-1-locks/$f.lock.json'))['sha256'])")"
  if [ "$d" = "$l" ]; then echo "  MATCH $f  $d"; else echo "  MISMATCH $f disk=$d lock=$l"; fi
done
echo "  git status for the three judges (must be empty):"
( cd "$REPO" && git status --porcelain tests/test_layout_paths.py tests/test_layout_paths_chunk2.py tests/test_layout_paths_chunk2a.py | sed 's/^/    /' )
echo

echo "########## §4.5 — plan-lint ##########"
for p in planning/layout-refactor/PLAN.md planning/layout-refactor/CHUNK-2a-SPEC.md; do
  ( cd "$REPO" && "$PY" tools/plan-lint.py "$p" ) > "$WORK/lint.out" 2>&1
  echo "  $p rc=$?  $(tail -1 "$WORK/lint.out")"
done
echo

echo "########## §4.6 — no renames; fence self-audit ##########"
( cd "$REPO" && git diff HEAD --name-status --find-renames | sed 's/^/  /' )
R="$( cd "$REPO" && git diff HEAD --name-status --find-renames | grep -c '^R' )"
echo "  rename entries: $R (must be 0 — this chunk moves nothing)"
echo

rm -rf "$WORK"
echo "done."

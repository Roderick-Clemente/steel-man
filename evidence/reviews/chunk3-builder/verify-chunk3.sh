#!/usr/bin/env bash
# verify-chunk3.sh — CHUNK-3-SPEC §4 exit criteria, run and captured (§9, §11).
#
# Every §4 criterion below is *run*, and its real number is printed next to the
# baseline the spec recorded, so a reviewer compares measurements rather than
# reading a claim. Nothing here asserts on an exit code alone (§7): each check
# prints the artifact it read — counts, file lists, git status letters, SHAs.
#
# Usage: bash verify-chunk3.sh [<commit-ish>]   (default HEAD)
#   §4.5 and §4.8 inspect a commit, so this runs AFTER the chunk-3 commit lands.
#
# Deliberately NOT `set -e`: a failing criterion must not abort the capture.
# Every check records PASS/FAIL into a tally and the script exits non-zero at the
# end if any failed — a partial capture that stops at the first problem is how a
# reviewer ends up with no numbers for the other seven criteria.
set -uo pipefail

COMMIT="${1:-HEAD}"
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT" || exit 2
PY=/private/tmp/asprint-venv/bin/python
HERE="evidence/phase-4.5/build-evidence/r-chunk3-builder-20260814"

FAILED=0
pass() { printf '  ==> PASS  %s\n' "$1"; }
fail() { printf '  ==> FAIL  %s\n' "$1"; FAILED=$((FAILED + 1)); }
hdr()  { printf '\n========== %s ==========\n' "$1"; }

printf 'chunk-D1-3 §4 exit-criteria capture\n'
printf 'commit under test : %s (%s)\n' "$(git rev-parse "$COMMIT")" "$COMMIT"
printf 'branch           : %s\n' "$(git rev-parse --abbrev-ref HEAD)"
printf 'worktree clean   : %s\n' "$([ -z "$(git status --porcelain)" ] && echo yes || echo NO)"

# ---------------------------------------------------------------- §4.1
hdr "§4.1 full suite on the suite interpreter"
printf 'interpreter      : %s\n' "$PY"
printf 'version          : %s\n' "$("$PY" -V 2>&1)"
printf 'NOT              : /usr/bin/python3 (%s, no pytest — chunk-2a §2.4 K2)\n' \
  "$(/usr/bin/python3 -V 2>&1)"
# Counts come from the junit XML, not from stdout. pytest.ini already sets -q;
# adding a second -q raises quiet level 2, which SUPPRESSES the "N passed" line
# entirely — a builder tailing that output sees no counts and is one step from
# hand-writing a number. The XML is the artifact (§7).
"$PY" -m pytest --tb=short --junit-xml=/tmp/chunk3-junit.xml > /tmp/chunk3-pytest.out 2>&1
PYTEST_RC=$?
"$PY" - <<'PYEOF'
import xml.etree.ElementTree as ET
r = ET.parse('/tmp/chunk3-junit.xml').getroot()
s = r.find('testsuite') if r.tag == 'testsuites' else r
a = s.attrib
total = int(a['tests']); fails = int(a['failures']); errs = int(a['errors'])
skips = int(a['skipped'])
print(f"collected={total} passed={total - fails - errs - skips} "
      f"failed={fails} errors={errs} skipped={skips}")
print("baseline entering chunk (spec §4.1): 213 passed, 3 skipped, plus the "
      "chunk-3 judge's 14")
for tc in s.iter('testcase'):
    for bad in list(tc.findall('failure')) + list(tc.findall('error')):
        print(f"  FAILING: {tc.get('classname')}::{tc.get('name')}")
PYEOF
if [ "$PYTEST_RC" -eq 0 ]; then pass "§4.1 suite green"; else
  fail "§4.1 suite not green (pytest rc=$PYTEST_RC) — see /tmp/chunk3-pytest.out"; fi

hdr "§4.1b chunk-3 judge in isolation"
"$PY" -m pytest tests/test_layout_paths_chunk3.py -v --tb=short 2>&1 | grep -E 'PASSED|FAILED|passed|failed'
CHUNK3_RC=${PIPESTATUS[0]}
[ "$CHUNK3_RC" -eq 0 ] && pass "§4.1b all 14 chunk-3 tests green" \
                       || fail "§4.1b chunk-3 judge rc=$CHUNK3_RC"

# ---------------------------------------------------------------- §4.2
hdr "§4.2 residual citation grep, scoped to the §2.1a surface"
# The spec's own command, verbatim in shape. zsh does not word-split unquoted
# expansions, so `for f in $LIST` reports 0 hits per file — a clean, completely
# false green. xargs -0 is used for exactly that reason (spec §4.2 hazard note).
ls -1 PRD.md AGENTS.md README.md \
      tools/OPERATING-RULES.md tools/README.md tools/KNOWN-ISSUES.md \
      tools/PHASE-0.5-CLOSE.md tools/RUN-LEDGER.md tools/REPRODUCE.md \
      skills/adversarial-sprint/SKILL.md skills/sprint-invocation/SKILL.md \
      tools/conventions/*.md tools/sprint_loop/prompts/*.md \
      droid-wiki/*.md planning/ROADMAP-REVIEW*.md > /tmp/citation-surface.txt
printf 'surface files    : %s (non-empty guard: %s)\n' \
  "$(wc -l < /tmp/citation-surface.txt | tr -d ' ')" \
  "$([ -s /tmp/citation-surface.txt ] && echo ok || echo EMPTY-LIST)"
tr '\n' '\0' < /tmp/citation-surface.txt \
  | xargs -0 grep -onE '(^|[^/A-Za-z0-9_.-])phase-[0-9]+(\.[0-9]+)?/' \
  > /tmp/chunk3-residuals.txt 2>/dev/null
RESID=$(wc -l < /tmp/chunk3-residuals.txt | tr -d ' ')
RESID_FILES=$(cut -d: -f1 < /tmp/chunk3-residuals.txt | sort -u)
printf 'residual hits    : %s (baseline on 0b1262c: 105 across 15 files)\n' "$RESID"
printf 'residual files   : %s\n' "$(echo "$RESID_FILES" | tr '\n' ' ')"
# Every surviving hit must be an enumerated historical-narrative exception.
UNLISTED=0
while IFS= read -r f; do
  [ -z "$f" ] && continue
  case "$f" in
    droid-wiki/by-the-numbers.md|droid-wiki/lore.md) ;;
    *) printf '  UNLISTED narrative file: %s\n' "$f"; UNLISTED=$((UNLISTED + 1)) ;;
  esac
done <<< "$RESID_FILES"
while IFS= read -r hit; do
  [ -z "$hit" ] && continue
  ref="$(echo "$hit" | cut -d: -f1,2)"
  grep -qF "$ref" planning/PATH-REDIRECTS.md || {
    printf '  NOT enumerated in PATH-REDIRECTS: %s\n' "$ref"
    UNLISTED=$((UNLISTED + 1))
  }
done < /tmp/chunk3-residuals.txt
[ "$UNLISTED" -eq 0 ] \
  && pass "§4.2 all $RESID residual hits are enumerated exceptions in 2 narrative files" \
  || fail "§4.2 $UNLISTED residual hit(s) unaccounted for"

hdr "§4.2b rewrite is idempotent (re-running changes nothing)"
"$PY" "$HERE/rewrite-citations.py" --check | tail -3
[ "${PIPESTATUS[0]}" -eq 0 ] && pass "§4.2b rewrite-citations.py --check: 0 further rewrites" \
                             || fail "§4.2b rewrite not idempotent"

hdr "§4.2c PATH-REDIRECTS matches its generator"
"$PY" "$HERE/gen-path-redirects.py" --check
[ $? -eq 0 ] && pass "§4.2c planning/PATH-REDIRECTS.md == generator output" \
             || fail "§4.2c PATH-REDIRECTS drifted from its generator"

# ---------------------------------------------------------------- §4.3
hdr "§4.3 evidence-internal citations are covered by the table (checklist, not a fix list)"
grep -rn --include='*.json' --include='*.raw.txt' --include='*.stream.json' \
  'phase-[0-9]' evidence/ > /tmp/chunk3-evidence-refs.txt 2>/dev/null
printf 'evidence lines carrying an old prefix : %s\n' \
  "$(wc -l < /tmp/chunk3-evidence-refs.txt | tr -d ' ')"
printf 'distinct files                        : %s\n' \
  "$(cut -d: -f1 < /tmp/chunk3-evidence-refs.txt | sort -u | wc -l | tr -d ' ')"
printf 'prefix table rows in PATH-REDIRECTS   : %s\n' \
  "$(grep -cE '^\| `phase-[0-9]' planning/PATH-REDIRECTS.md)"
# Coverage: every distinct bare prefix seen in evidence has a table row.
"$PY" - <<'PYEOF'
import re, pathlib
seen = set()
for line in pathlib.Path('/tmp/chunk3-evidence-refs.txt').read_text(
        encoding='utf-8', errors='replace').splitlines():
    for m in re.finditer(r'(?:^|[^/A-Za-z0-9_.\-])(phase-[0-9]+(?:\.[0-9]+)?/)', line):
        seen.add(m.group(1))
table = pathlib.Path('planning/PATH-REDIRECTS.md').read_text(encoding='utf-8')
rows = set(re.findall(r'^\| `(phase-[0-9][^`]*)`', table, re.MULTILINE))
missing = sorted(p for p in seen if not any(r.startswith(p) for r in rows))
print(f"distinct old prefixes in evidence: {len(seen)} -> {' '.join(sorted(seen))}")
print(f"uncovered by any table row      : {len(missing)} {missing}")
raise SystemExit(1 if missing else 0)
PYEOF
[ $? -eq 0 ] && pass "§4.3 every evidence-internal prefix has a redirect row" \
             || fail "§4.3 evidence carries a prefix with no redirect row"

# ---------------------------------------------------------------- §4.4
hdr "§4.4 relative-link resolution (count checked reported next to count dead)"
"$PY" "$HERE/dead-links.py"
DEAD_RC=$?
printf 'baseline dead before this chunk: 4 (all README, §2.5)\n'
[ "$DEAD_RC" -eq 0 ] && pass "§4.4 0 dead links, resolver examined a non-zero set" \
                     || fail "§4.4 dead-links.py rc=$DEAD_RC"

# ---------------------------------------------------------------- §4.5
hdr "§4.5 LEDGER rename verified"
printf 'evidence/LEDGER.md exists          : %s\n' \
  "$([ -f evidence/LEDGER.md ] && echo yes || echo NO)"
printf 'planning/phase-4.5/LEDGER.md gone  : %s\n' \
  "$([ ! -e planning/phase-4.5/LEDGER.md ] && echo yes || echo STILL-THERE)"
printf 'tracked at new path                : %s\n' \
  "$(git ls-files --error-unmatch evidence/LEDGER.md >/dev/null 2>&1 && echo yes || echo NO)"
printf 'tracked at old path                : %s\n' \
  "$(git ls-files --error-unmatch planning/phase-4.5/LEDGER.md >/dev/null 2>&1 \
      && echo STILL-TRACKED || echo no)"
FOLLOW=$(git log --follow --format=%H -- evidence/LEDGER.md | wc -l | tr -d ' ')
printf '%s\n' "git log --follow reaches commits    : $FOLLOW (must be > 1)"
RENAME_SHA=$(git log --follow --diff-filter=R --format=%H -- evidence/LEDGER.md | head -1)
printf 'rename commit                      : %s\n' "${RENAME_SHA:-NONE}"
# Two numstat forms, both printed, because they disagree and the disagreement
# IS the finding (see FINDINGS §F13). A pathspec filters the source side out of
# the tree diff BEFORE rename detection runs, so the destination reads as a
# fresh add. Reproduced in a scratch repo on a single pure `git mv`:
#   git show --numstat --format= HEAD -- b/F.md   ->  3  0  b/F.md
#   git show --numstat --format= HEAD             ->  0  0  {a => b}/F.md
# The judge (test_chunk3_ledger_rename_carried_no_content_edit) uses the first
# form, so it cannot go green on a correct rename. §4.5 is judged on the forms
# that can actually observe a rename, and the judge's form is reported beside
# them rather than hidden.
NUMSTAT_PATHSPEC=$(git show "${RENAME_SHA:-$COMMIT}" --numstat --format= -- evidence/LEDGER.md | head -1)
NUMSTAT_FOLLOW=$(git log --follow --numstat --format= -1 "${RENAME_SHA:-$COMMIT}" -- evidence/LEDGER.md | head -1)
SIMILARITY=$(git show --name-status --find-renames --format= "${RENAME_SHA:-$COMMIT}" \
             | grep 'evidence/LEDGER.md' | cut -f1)
printf '%s\n' "numstat, judge's form (pathspec)   : ${NUMSTAT_PATHSPEC:-EMPTY}  <- add-shaped, see F13"
printf '%s\n' "numstat, git log --follow form     : ${NUMSTAT_FOLLOW:-EMPTY}"
printf '%s\n' "rename similarity index            : ${SIMILARITY:-NONE} (R100 == byte-identical)"
ADDED=$(echo "$NUMSTAT_FOLLOW" | awk '{print $1}')
DELETED=$(echo "$NUMSTAT_FOLLOW" | awk '{print $2}')
printf 'added=%s deleted=%s (both must be 0 — the ledger is append-only, §5)\n' \
  "${ADDED:-?}" "${DELETED:-?}"
if [ -f evidence/LEDGER.md ] && [ ! -e planning/phase-4.5/LEDGER.md ] \
   && [ "$FOLLOW" -gt 1 ] && [ -n "$RENAME_SHA" ] \
   && [ "$ADDED" = "0" ] && [ "$DELETED" = "0" ] && [ "$SIMILARITY" = "R100" ]; then
  pass "§4.5 rename carries history with zero content edit (R100, +0/-0)"
else
  fail "§4.5 rename not verified"
fi

# ---------------------------------------------------------------- §4.6
hdr "§4.6 tools/wiki-link-audit.py"
"$PY" tools/wiki-link-audit.py
WIKI_RC=$?
printf 'rc=%s (baseline on 0b1262c: 61 pages, all zero, rc=0)\n' "$WIKI_RC"
printf 'NOTE: this walks droid-wiki/ ONLY (wiki-link-audit.py:24,:88). It is NOT\n'
printf '      a substitute for §4.4 — it reports dead=0 on the very commit where\n'
printf '      README.md carried four dead links (§7 silent-green shape).\n'
[ "$WIKI_RC" -eq 0 ] && pass "§4.6 wiki-link-audit rc=0" || fail "§4.6 rc=$WIKI_RC"

# ---------------------------------------------------------------- §4.7
hdr "§4.7 tools/plan-lint.py"
# The spec writes "`tools/plan-lint.py` rc=0" with no argument, but the tool
# takes a required positional `plan` — bare invocation is argparse rc=2, which
# would read as a chunk failure that is really a missing argument. Linted on the
# same two documents the earlier chunks used: the parent PLAN and this chunk's
# own spec. Warnings do not set rc; only structural errors do.
LINT_RC=0
for plan in planning/layout-refactor/PLAN.md planning/layout-refactor/CHUNK-3-SPEC.md; do
  "$PY" tools/plan-lint.py "$plan" > "/tmp/chunk3-plan-lint-$(basename "$plan").out" 2>&1
  rc=$?
  printf '%-46s rc=%s  %s\n' "$plan" "$rc" \
    "$(grep -oE '(PASS|FAIL)[^|]*' "/tmp/chunk3-plan-lint-$(basename "$plan").out" | head -1)"
  [ "$rc" -ne 0 ] && LINT_RC=$rc
done
[ "$LINT_RC" -eq 0 ] && pass "§4.7 plan-lint rc=0 on PLAN.md and CHUNK-3-SPEC.md" \
                     || fail "§4.7 rc=$LINT_RC"

# ---------------------------------------------------------------- §4.8
hdr "§4.8 scope containment on $COMMIT"
git show --name-status --find-renames --format= "$COMMIT" > /tmp/chunk3-diffshape.txt
printf 'status letters   : %s\n' \
  "$(cut -f1 < /tmp/chunk3-diffshape.txt | sort | uniq -c | tr '\n' ' ')"
printf 'renames (R):\n'
grep -E '^R' /tmp/chunk3-diffshape.txt | sed 's/^/  /'
R_COUNT=$(grep -cE '^R' /tmp/chunk3-diffshape.txt)
R_OK=$(grep -E '^R' /tmp/chunk3-diffshape.txt \
       | grep -c 'planning/phase-4.5/LEDGER.md.*evidence/LEDGER.md')
printf 'rename count=%s, the LEDGER rename present=%s (both must be 1)\n' \
  "$R_COUNT" "$R_OK"
printf 'modified (M) under evidence/:\n'
grep -E '^M' /tmp/chunk3-diffshape.txt | grep 'evidence/' | sed 's/^/  /' || true
M_EVIDENCE=$(grep -E '^M' /tmp/chunk3-diffshape.txt | grep -c 'evidence/')
printf 'M-under-evidence=%s (must be 0 — committed evidence is immutable, §5/§21)\n' \
  "$M_EVIDENCE"
TOKENS=$(grep -c 'evidence/phase-4.5/tokens/' /tmp/chunk3-diffshape.txt)
printf 'paths under evidence/phase-4.5/tokens/=%s (must be 0 — §22, the builder\n' "$TOKENS"
printf '  seat holds no signing key and writes no token)\n'
printf 'judge files in the diff (must be none):\n'
grep -E 'tests/test_layout_paths' /tmp/chunk3-diffshape.txt | sed 's/^/  /' || true
JUDGES=$(grep -cE 'tests/test_layout_paths' /tmp/chunk3-diffshape.txt)
printf 'locked judge edits=%s (must be 0 — framework invariant #3)\n' "$JUDGES"
SPECS=$(grep -c 'planning/layout-refactor/' /tmp/chunk3-diffshape.txt)
printf 'planning/layout-refactor/ edits=%s (must be 0 — §2.1b)\n' "$SPECS"
PHASEN=$(grep -E 'planning/phase-[0-9]' /tmp/chunk3-diffshape.txt \
         | grep -vc 'LEDGER.md')
printf 'planning/phase-N/ edits (excl. the LEDGER rename)=%s (must be 0 — §2.1b)\n' "$PHASEN"
if [ "$R_COUNT" = "1" ] && [ "$R_OK" = "1" ] && [ "$M_EVIDENCE" = "0" ] \
   && [ "$TOKENS" = "0" ] && [ "$JUDGES" = "0" ] && [ "$SPECS" = "0" ] \
   && [ "$PHASEN" = "0" ]; then
  pass "§4.8 diff shape contained"
else
  fail "§4.8 diff shape out of scope"
fi

# ------------------------------------------------- extra: generated mirrors
hdr "extra — .cursor/rules/*.mdc mirrors regenerate to byte-identical content"
# Not in the §2.1a allowlist, but tests/test_sprint_loop.py:1698
# (…cursor_mdc_body_matches_canonical_g6) pins the .mdc body to the SKILL.md
# body, so editing an allowlisted SKILL.md without regenerating reddens the
# suite. Regenerated through the sanctioned script (§14), never hand-edited.
BEFORE=$(shasum -a 256 .cursor/rules/*.mdc)
./tools/install-skill.sh cursor > /dev/null 2>&1
AFTER=$(shasum -a 256 .cursor/rules/*.mdc)
printf '%s\n' "$AFTER"
[ "$BEFORE" = "$AFTER" ] \
  && pass "on-disk .mdc == tools/install-skill.sh cursor output" \
  || fail ".mdc drifted from the generator"

hdr "RESULT"
printf 'failed criteria: %s\n' "$FAILED"
[ "$FAILED" -eq 0 ] && printf 'chunk-D1-3 §4: ALL CRITERIA PASS\n' \
                    || printf 'chunk-D1-3 §4: %s CRITERION(A) FAILED\n' "$FAILED"
exit "$FAILED"

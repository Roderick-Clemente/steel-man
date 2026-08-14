#!/usr/bin/env bash
# tools/d1-exit-check.sh — CHUNK-4-SPEC §2.3 optional helper, §3.3/§3.4 exit
# checks scripted rather than run by hand (§9). Committed code, not evidence.
#
# Runs the four direct real script invocations against the valid-RED fixture
# (tests/fixtures/phase-1/valid-red/) plus the wiki-link-audit and full-suite
# exit checks, and prints the artifact each check read rather than asserting
# on an exit code alone (§7).
#
# verify-green.py against the fixture AS COMMITTED must REFUSE — the fixture
# is deliberately pre-fix on disk (§2.1's "fails pre-fix"). To also observe
# the real RED->GREEN transition the same spec requires, this script copies
# the fixture into a scratch dir, applies the documented one-line fix to
# subject.py there, and re-verifies GREEN against the SAME lock file. Two
# verify-green.py runs, two different verdicts, same lock hash — that
# disagreement is the evidence, not a flake.
set -uo pipefail

REPO_ROOT="$(git -C "$(dirname "${BASH_SOURCE[0]}")/.." rev-parse --show-toplevel)"
cd "$REPO_ROOT" || exit 2
PY="${D1_PYTHON:-python3}"
FIXTURE_DIR="tests/fixtures/phase-1/valid-red"
ASSERTION="running_total dropped the final cumulative value"

FAILED=0
pass() { printf '  ==> PASS  %s\n' "$1"; }
fail() { printf '  ==> FAIL  %s\n' "$1"; FAILED=$((FAILED + 1)); }
hdr()  { printf '\n========== %s ==========\n' "$1"; }

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
LOCKDIR="$WORK/locks"
FIXED="$WORK/fixed"
mkdir -p "$LOCKDIR" "$FIXED"

printf 'chunk-D1-4 exit-check capture\n'
printf 'interpreter : %s (%s)\n' "$PY" "$("$PY" -V 2>&1)"

# ---------------------------------------------------------------- §3.3.2
hdr "§3.3.2 valid-red.py classifies the fixture VALID"
"$PY" tools/phase-1-scripts/valid-red.py \
  --pilot-root "$REPO_ROOT" \
  --test-file "$FIXTURE_DIR/test_valid_red.py" \
  --accepted-assertion "$ASSERTION" \
  -o json > "$WORK/valid-red.json"
VR_RC=$?
grep -q '"valid": true' "$WORK/valid-red.json" && VR_CLASSIFIED=true || VR_CLASSIFIED=false
printf 'exit=%s classified-valid=%s\n' "$VR_RC" "$VR_CLASSIFIED"
[ "$VR_RC" -eq 0 ] && [ "$VR_CLASSIFIED" = true ] \
  && pass "§3.3.2 valid-red.py: VALID, exit 0" \
  || fail "§3.3.2 valid-red.py did not classify VALID"

# ---------------------------------------------------------------- §3.3.1
hdr "§3.3.1 lock.py locks the fixture"
"$PY" tools/phase-1-scripts/lock.py \
  "$FIXTURE_DIR/test_valid_red.py" "$ASSERTION" \
  --pilot-root "$REPO_ROOT" --locks-dir "$LOCKDIR"
LOCK_RC=$?
LOCK_FILE="$LOCKDIR/$FIXTURE_DIR/test_valid_red.py.lock.json"
printf 'exit=%s lock-file=%s\n' "$LOCK_RC" "$([ -f "$LOCK_FILE" ] && echo written || echo MISSING)"
[ "$LOCK_RC" -eq 0 ] && [ -f "$LOCK_FILE" ] \
  && pass "§3.3.1 lock.py: manifest written, exit 0" \
  || fail "§3.3.1 lock.py failed"

# ---------------------------------------------------------------- §3.3.3a
hdr "§3.3.3a verify-green.py refuses on the fixture AS COMMITTED (expected RED)"
"$PY" tools/phase-1-scripts/verify-green.py \
  --pilot-root "$REPO_ROOT" --lock-file "$LOCK_FILE" \
  --test-file "$FIXTURE_DIR/test_valid_red.py" > "$WORK/verify-red.out" 2>&1
VG_RED_RC=$?
head -1 "$WORK/verify-red.out"
# A committed fixture that ever reports GREEN as-is is not testing anything —
# rc!=0 here IS the pass condition.
[ "$VG_RED_RC" -ne 0 ] && grep -q 'GREEN REFUSED' "$WORK/verify-red.out" \
  && pass "§3.3.3a verify-green.py correctly refuses GREEN pre-fix" \
  || fail "§3.3.3a verify-green.py did not refuse pre-fix (fixture no longer RED?)"

hdr "§3.3.3b verify-green.py accepts GREEN after the one-line subject.py fix"
cp "$FIXTURE_DIR/test_valid_red.py" "$FIXTURE_DIR/subject.py" "$FIXED/"
sed -i.bak 's/return totals\[:-1\]/return totals/' "$FIXED/subject.py" && rm -f "$FIXED/subject.py.bak"
"$PY" tools/phase-1-scripts/verify-green.py \
  --pilot-root "$FIXED" --lock-file "$LOCK_FILE" \
  --test-file test_valid_red.py > "$WORK/verify-green.out" 2>&1
VG_GREEN_RC=$?
head -1 "$WORK/verify-green.out"
[ "$VG_GREEN_RC" -eq 0 ] && grep -q 'GREEN ACCEPTED' "$WORK/verify-green.out" \
  && pass "§3.3.3b verify-green.py: real RED->GREEN observed, same lock hash" \
  || fail "§3.3.3b verify-green.py did not accept GREEN post-fix"

# ---------------------------------------------------------------- §3.3.4
hdr "§3.3.4 local_backend.py signs a bundle with a TEST key (never the referee's)"
EVIDENCE_SIGNING_KEY=test-key "$PY" tools/phase-3.2-evidence/local_backend.py \
  --pilot-root "$FIXED" --framework-root "$REPO_ROOT" \
  --test-file test_valid_red.py --lock-file "$LOCK_FILE" \
  --output "$WORK/bundle.json" \
  --signing-key-env EVIDENCE_SIGNING_KEY --key-id d1-exit-check-test-key \
  > "$WORK/local-backend.out" 2>&1
LB_RC=$?
tail -3 "$WORK/local-backend.out"
[ "$LB_RC" -eq 0 ] && [ -f "$WORK/bundle.json" ] \
  && pass "§3.3.4 local_backend.py: signed bundle written, exit 0, test key only" \
  || fail "§3.3.4 local_backend.py failed"

# ---------------------------------------------------------------- §3.4.1
hdr "§3.4.1 tools/wiki-link-audit.py"
"$PY" tools/wiki-link-audit.py
WIKI_RC=$?
[ "$WIKI_RC" -eq 0 ] && pass "§3.4.1 wiki-link-audit rc=0" || fail "§3.4.1 rc=$WIKI_RC"

# ---------------------------------------------------------------- §3.4.2
hdr "§3.4.2 full suite (junit XML count, not -q stdout — F11)"
JUNIT="$WORK/junit.xml"
"$PY" -m pytest --tb=short --junit-xml="$JUNIT" > "$WORK/pytest.out" 2>&1
SUITE_RC=$?
"$PY" - "$JUNIT" <<'PYEOF'
import sys, xml.etree.ElementTree as ET
r = ET.parse(sys.argv[1]).getroot()
s = r.find('testsuite') if r.tag == 'testsuites' else r
a = s.attrib
total = int(a['tests']); fails = int(a['failures']); errs = int(a['errors']); skips = int(a['skipped'])
print(f"collected={total} passed={total - fails - errs - skips} failed={fails} errors={errs} skipped={skips}")
for tc in s.iter('testcase'):
    for bad in list(tc.findall('failure')) + list(tc.findall('error')):
        print(f"  FAILING: {tc.get('classname')}::{tc.get('name')}")
PYEOF
[ "$SUITE_RC" -eq 0 ] && pass "§3.4.2 full suite green" || fail "§3.4.2 suite rc=$SUITE_RC"

hdr "RESULT"
printf 'failed criteria: %s\n' "$FAILED"
[ "$FAILED" -eq 0 ] && printf 'chunk-D1-4 exit-check: ALL PASS\n' \
                    || printf 'chunk-D1-4 exit-check: %s CRITERION(A) FAILED\n' "$FAILED"
exit "$FAILED"

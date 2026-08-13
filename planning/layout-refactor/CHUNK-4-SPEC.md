# CHUNK-4-SPEC — exit check: direct real script invocations + path-existence test

**Parent PLAN:** `planning/layout-refactor/PLAN.md` v3 (`ed98cd3`)
**Branch:** `factory/layout-refactor`
**Chunk ID:** `chunk-D1-4`
**Predecessor:** `chunk-D1-3` (must have verified signed token)
**Successor gate:** none (last chunk of D1; D2 opens only after D1 closes)

## 1. Problem statement (§13)

The D1 exit criteria must be checked, not assumed (§11). v2's
"real (non-dry) fixture run" via `python3 tools/sprint-loop.py ...`
**structurally cannot exit 0**: `sprint-loop.py`'s reconcile gate
reads stdin → EOF → `SystemExit(1)` before the chunk loop;
`produce_evidence` raises `RuntimeError` without
`EVIDENCE_SIGNING_KEY`; `commit_chunk_change` would `git checkout -b`
off the branch mid-verify. This chunk replaces the full-runner
invocation with **direct real invocations of the four moved
scripts** against a valid-RED fixture + a path-existence test. No
full-runner invocation.

minimax-m3 v3 REJECT noted that the exact CLI argument shapes for
the four scripts were not anchored in v2/v3. This spec requires the
executor to verify the actual argument shapes (by reading each
script's `--help` or argparse) before writing the exit-check
commands, and to record the verified shapes in the spec's
implementation log.

## 2. Surface touched

### 2.1 New fixture: `tests/fixtures/phase-1/valid-red/test_valid_red.py`

A test that fails with a real `AssertionError` for a valid
behavioral reason — NOT a syntax error or tautology, so
`valid-red.py` classifies it as VALID (exit 0), not rejected.

The fixture must be:
- A minimal Python test file with one `assert` that fails for a
  clear behavioral reason (e.g. `assert 1 + 1 == 3`).
- Importable by pytest (no missing dependencies).
- Fixable: it fails pre-fix, passes post-fix (a one-line change
  makes it pass).

The executor must verify that `valid-red.py` classifies this
fixture as VALID before using it in the exit check.

### 2.2 New test: `tests/test_layout_paths.py` (grow the Chunk-1 file)

Add a fourth test to the file created in Chunk 1:

**Test 4 — path-existence assertion:** assert that the constructed
script paths resolve to files that exist on disk:
- `SCRIPTS_ROOT / "lock.py"` → `tools/phase-1-scripts/lock.py` exists
- `SCRIPTS_ROOT / "valid-red.py"` → `tools/phase-1-scripts/valid-red.py` exists
- `SCRIPTS_ROOT / "verify-green.py"` → `tools/phase-1-scripts/verify-green.py` exists
- `EVIDENCE_CODE_ROOT / "local_backend.py"` → `tools/phase-3.2-evidence/local_backend.py` exists

This is the belt-and-suspenders check that does not depend on
running the scripts.

### 2.3 Exit-check script (optional helper)

The executor MAY create a small `tools/d1-exit-check.sh` (or `.py`)
that runs the four direct invocations in §3 and exits 0 only if all
four succeed. This is optional — the executor may also run the
four invocations directly in the verify step. If created, the
helper is committed (it is code, not evidence).

## 3. What the executor MUST do

### 3.1 Verify the actual CLI argument shapes

Before writing the exit-check commands, the executor MUST read
each script's `--help` or argparse to verify the exact argument
shapes. Record the verified shapes in the commit message or a
implementation log. The four scripts are:
- `tools/phase-1-scripts/lock.py`
- `tools/phase-1-scripts/valid-red.py`
- `tools/phase-1-scripts/verify-green.py`
- `tools/phase-3.2-evidence/local_backend.py`

### 3.2 Create the valid-RED fixture

Create `tests/fixtures/phase-1/valid-red/test_valid_red.py` per
§2.1. Verify that `valid-red.py` classifies it as VALID.

### 3.3 Run the four direct real script invocations

Run each of the four moved scripts against the fixture (or a test
signing key for `local_backend.py`). Each must exit 0. If any path
is broken by the move, the invocation crashes with
`FileNotFoundError` (python exit 2) or `RuntimeError` — the §7
reality-assertion the dry-run was structurally blind to.

The exact argument shapes are to be verified by the executor per
§3.1. The invocations are (approximately — executor verifies):
1. `lock.py` against the fixture → writes a lock manifest
2. `valid-red.py` against the fixture → classifies as VALID (exit 0)
3. `verify-green.py` against the fixture → verifies hash + test passes
4. `local_backend.py` with `EVIDENCE_SIGNING_KEY=test-key` → produces a signed bundle

### 3.4 Run the exit checks

1. `python3 tools/wiki-link-audit.py` → green
2. `python3 -m pytest -q` → 198 tests green (197 from chunks 1-3 + 1 new path-existence test)
3. The four direct script invocations (§3.3) all exit 0
4. `git log --stat` shows the expected commits on
   `factory/layout-refactor`

### 3.5 Commit + push

Commit with message `chunk-4: D1 exit check — direct script invocations + path-existence test`.
Push to `origin/factory/layout-refactor`.

## 4. Verify (§11 exit checks — the D1 gate)

### 4.1 wiki-link-audit green

`python3 tools/wiki-link-audit.py` → green (no dead links).

### 4.2 Full suite green

`python3 -m pytest -q` → 198 tests, all green (194 pre-existing +
3 from Chunk 1 + 1 new path-existence test from Chunk 4).

### 4.3 Direct script invocations all exit 0

The four invocations in §3.3 all exit 0 without
`FileNotFoundError`. This is the core §7 reality-assertion — the
moved scripts work at their new paths.

### 4.4 Path-existence test passes

`tests/test_layout_paths.py` test 4 (§2.2) passes — the constructed
script paths resolve to files that exist on disk.

### 4.5 Post-D1 git log

`git log --stat` shows exactly N + 1 commits landed on
`factory/layout-refactor` since branching from `main` (PLAN + Chunk
1-4 commits), each with a signed token in
`evidence/phase-4.5/tokens/` whose HMAC verifies and whose
`chunk_commit_sha` matches the chunk's HEAD.

## 5. What NOT to do (fences)

- **Do NOT use `--dry-run` as the exit check.** Dry-run branches
  bypass the real `subprocess.run` calls; they cannot catch broken
  paths. This is the v1/v2 finding this chunk fixes.
- **Do NOT invoke `sprint-loop.py` as the exit check.** The
  reconcile gate reads stdin → EOF → `SystemExit(1)`;
  `produce_evidence` raises `RuntimeError` without
  `EVIDENCE_SIGNING_KEY`; `commit_chunk_change` would `git checkout
  -b` off the branch. Use direct script invocations instead.
- **Do NOT edit evidence bytes.**
- **Do NOT touch `main`.**
- **Do NOT hold `EVIDENCE_SIGNING_KEY` (the referee's key) for
  chunk-close.** The `local_backend.py` invocation in §3.3 uses a
  TEST key (`EVIDENCE_SIGNING_KEY=test-key`), not the referee's
  real key. The builder never holds the referee's key.
- **Do NOT write to `phase-4.5/tokens/` or
  `evidence/phase-4.5/tokens/`.** The referee signs; the builder
  does not.

## 6. STOP conditions (§5)

If any exit check fails after one bounded fix attempt:
- Suite red after one fix → STOP
- A script invocation crashes with `FileNotFoundError` after one
  fix → STOP
- `wiki-link-audit` red after one fix → STOP
- Any evidence-path policy ambiguity → STOP

On STOP: commit a `BLOCKED-with-evidence` note on the branch, post
`BLOCKED: chunk=chunk-D1-4 reason=<...>` to `STEER.md`, and halt
the deliverable. An incomplete night with clean tokens beats a
complete night without.

## 7. Rule application

| Rule | Where |
|------|-------|
| §5 | §6 STOP conditions |
| §7 | §4.3 direct script invocations assert on reality, not exit codes or dry-run strings |
| §11 | §4 exit checks are real script runs + path-existence test, not assumptions |
| §13 | this spec states the problem + constraints; the executor verifies the arg shapes and records them |
| §18.2 | one chunk, one commit |
| §18.3 | per-chunk verify block (§4) |
| §21 | no evidence bytes edited |
| §22 | builder uses a TEST key for local_backend.py, not the referee's key |

## 8. Chunk-close protocol

Same as CHUNK-1-SPEC §8, with `chunk=chunk-D1-4`. This is the last
chunk of D1; D2 opens only after D1 closes with a verified token.

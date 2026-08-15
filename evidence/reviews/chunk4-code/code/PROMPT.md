# Cross-family code review: chunk-D1-4 (D1 exit check — valid-RED fixture + direct script invocations)

You are an independent Tier-2 reviewer. Adversarial, evidence-first.
Do not defer to the builder, the planner, or to any earlier review.

## What to review

Repo: `/Users/factory/work/adversarial-sprint-dev`
Branch: `factory/layout-refactor`
Build commit under review: **20a3041**
Spec: `planning/layout-refactor/CHUNK-4-SPEC.md`
Chunk-4 judge: `tests/test_layout_paths_chunk4.py`
  (sha256 `7333fa628daca5bf550730eb6f8c6115e2c9300204c28401dd93ceca85c7608c`,
  locked at `tools/phase-1-locks/tests/test_layout_paths_chunk4.py.lock.json`)
Chunk-1 judge: `tests/test_layout_paths.py` (sha256 `cb00dfac…`, skips post-flip)
Chunk-2 judge: `tests/test_layout_paths_chunk2.py` (sha256 `48a579f8…`)
Chunk-2a judge: `tests/test_layout_paths_chunk2a.py` (sha256 `7289ca09…`)
Chunk-3 judge: `tests/test_layout_paths_chunk3.py` (sha256 `5c66bcfc…`)
Diff of the build: `build.diff` in this directory.

Suite interpreter: `/private/tmp/asprint-venv/bin/python` (3.13.3). **This is not
`/usr/bin/python3`**, which is 3.9.6 and has no pytest installed. If the venv
path does not exist on your machine, build your own and report the path and
version. Do NOT report counts from 3.9.6 — it has no pytest.

This is the **last chunk of D1**. D2 opens only after D1 closes. The chunk
replaces the full-runner invocation (which structurally cannot exit 0) with
direct real invocations of the four moved scripts against a valid-RED fixture,
plus a path-existence test.

The builder filed 3 findings (F-A, F-B, F-C). F-A (BLOCKED: Test 4 required
editing a locked judge) was resolved by the planner creating a separate
`tests/test_layout_paths_chunk4.py` at a later commit, ratified and locked by
the referee. F-B (stale "198 tests" figure) and F-C (stale "origin" push
target) are spec errata.

## Your job — challenge these, in order

1. **Is the valid-RED fixture actually valid?** The fixture at
   `tests/fixtures/phase-1/valid-red/test_valid_red.py` must fail with a real
   `AssertionError` for a valid behavioral reason (not a syntax error,
   tautology, or import failure). Run
   `python3 tools/phase-1-scripts/valid-red.py tests/fixtures/phase-1/valid-red/test_valid_red.py`
   and confirm it classifies the fixture as VALID (exit 0). Then check
   `subject.py`: does the one-line fix produce a real RED→GREEN transition
   when verified by `verify-green.py`? A fixture that is VALID for the wrong
   reason (e.g. raises before the assert) is a silent-green shape.

2. **Do the four direct script invocations all exit 0?** The builder claims
   all four moved scripts (`lock.py`, `valid-red.py`, `verify-green.py`,
   `local_backend.py`) can be invoked directly and exit 0. Run
   `tools/d1-exit-check.sh` and verify. Check the CLI argument shapes the
   builder recorded against each script's actual `--help` output — a mismatch
   means the invocation works by accident, not by correct argument
   construction.

3. **Is the path-existence test correct?** The chunk-4 judge asserts that
   `SCRIPTS_ROOT / "lock.py"`, `SCRIPTS_ROOT / "valid-red.py"`,
   `SCRIPTS_ROOT / "verify-green.py"`, and `EVIDENCE_CODE_ROOT /
   "local_backend.py"` all resolve to files that exist on disk. Verify each
   path resolves. Mutate one root in a sandbox and confirm the test fails —
   a test that cannot fail is not a test.

4. **Is `wiki-link-audit.py` rc=0?** Run it. The builder claims 61 pages, all
   zero dead links. Verify the count and that zero dead links is correct
   (not that the tool silently skips broken links).

5. **Are all five judges byte-unchanged?** Hash each judge file and compare to
   the lock manifests under `tools/phase-1-locks/tests/`. The builder may not
   modify the test that judges it (invariant 3). The chunk-4 judge was
   authored by the planner and locked by the referee at a later commit —
   confirm the on-disk hash matches the lock.

6. **Is the suite green at the right counts?** Run
   `/private/tmp/asprint-venv/bin/python -m pytest -q` (or your own venv if
   that path does not exist). Expected **236 passed, 3 skipped**. Report the
   counts you observe and the interpreter path you used. The builder's F-B
   notes the spec's "198" figure is stale — confirm the actual count and
   flag any discrepancy.

7. **Scope escapes.** This chunk creates a fixture, an exit-check script, and
   a judge file. Any file outside that set in `git show 20a3041
   --name-status` is a scope escape. Confirm nothing was written under
   `evidence/phase-4.5/tokens/` (the builder does not hold the signing key,
   §22). Confirm the fixture directory `tests/fixtures/phase-1/valid-red/`
   is new, not a modification of existing fixtures.

8. **D1 completeness.** This is the last D1 chunk. Does the D1 exit check
   actually verify what D1 was supposed to deliver? The four moved scripts
   (lock.py, valid-red.py, verify-green.py, local_backend.py) were routed
   by chunks 1-2. Do the direct invocations prove they work at their new
   homes? Is anything D1 was supposed to deliver still missing or unverified?

9. **Audit the spec and findings.** The builder filed F-A (BLOCKED, resolved),
   F-B (stale test count), F-C (stale push target). Are there issues the
   builder should have filed but did not? Is the spec's §3.5 "origin" push
   target the only stale reference, or are there more?

10. **D2 safety.** D2 opens after this gate closes. Does anything in this
    build make D2 harder or unsafe? The valid-RED fixture and exit-check
    script are new infrastructure — will they work correctly when D2's
    chunks are built and verified?

## Rules

- Cite `file:line` for every finding. No finding without evidence.
- If you assert a site is missed or a path changes, SHOW the before and
  after strings.
- Verify claims yourself. The spec and this prompt may both be wrong.
- Distinguish severity honestly: `blocker` (chunk cannot close),
  `high`, `medium`, `low`, `nit`.
- If something is genuinely correct, say so briefly and specifically.
- Note the Python interpreter path and version in your report.
- Do not commit, stage, or modify anything. You are read-only
  plus `Execute`; a review that mutates the artifact under review is void.

## Required output

Findings as a list, each with:
```
- severity: blocker|high|medium|low|nit
  category: correctness|spec-deviation|silent-green|factual|sequencing
  section: <file:line or spec §>
  claim: <what the artifact asserts or does>
  evidence: <what you found, with file:line and strings>
  recommended_change: <specific>
```

End with exactly one line:

`VERDICT: ACCEPT` or `VERDICT: ACCEPT-WITH-NITS` or `VERDICT: REJECT`

# Phase 4, Track A — Cheap closures + Act 1 packaging

You are executing **Phase 4 Track A** of the adversarial sprint framework. This
track is parallel and non-gating — it does not block Track B or Track C. The
work is mechanical extraction and packaging of artifacts that already exist.

## Context

The project root is the repository containing `PRD.md` (this file's parent
directory). The pilot repo is at `/Users/factory/work/quantum-bank--llms-txt-pilot`.
Read `ROADMAP-REVIEW.md` for the full project audit. Read `PRD.md` for the spec.

## Tasks

### A1. Run `valid-red.py` against the existing locked test

**Problem:** Phase 1 shipped `phase-1/scripts/valid-red.py` but it was never
actually run. The RED was read from the test-designer's envelope instead of
being independently verified by the classifier. This is a gap in the Phase 1
exit criteria.

**Steps:**
1. Read `phase-1/valid-red.md` for the classifier's specification.
2. Read `phase-1/scripts/valid-red.py` for the implementation.
3. Read `phase-1/locks/test/test_llms_txt_charset.py.lock.json` for the lock
   manifest (contains the accepted assertion phrase and locked test sha).
   This is the Phase 1 charset lock — NOT the Phase 3 profile lock.
4. Check out the pre-fix commit of the pilot repo (the commit where the
   doubled-charset bug exists but the fix has not been applied). The lock
   manifest or `phase-1/RUN-LEDGER.md` should reference the exact commit.
5. Run `valid-red.py` against the locked test at that commit. The test should
   fail (RED) and the classifier should accept the RED as valid (fails for the
   expected reason, not a syntax/import/fixture error).
6. Record the output as evidence in `phase-1/build-evidence/valid-red-result.txt`.
7. Create 1-2 invalid-RED scenarios (e.g., introduce a syntax error, comment
   out the assertion) and verify the classifier rejects them. Record these
   in the same evidence file. (A2 creates the permanent fixtures; these are
   quick inline checks.)

**Exit:** `valid-red.py` has been run, the RED is accepted, invalid REDs are
rejected, and the evidence is on disk.

### A2. Create 3-4 invalid-RED fixtures

**Problem:** Phase 1 never demonstrated that invalid REDs are rejected. The
classifier has rejection criteria documented in `phase-1/valid-red.md` but
no test fixtures exercise them.

**Steps:**
1. Create fixture test files in `phase-1/fixtures/invalid-red/` that trigger
   each rejection category:
   - **Syntax/import failure:** a test file with a `SyntaxError` or
     `ModuleNotFoundError`.
   - **Tautological test:** `assert True` or `assert 1 == 1`.
   - **Subject under test mocked:** `MagicMock` for the SUT.
   - **No failure (green):** a test that passes (exit code 0).
2. Run `valid-red.py` against each fixture and confirm the classifier rejects
   each one with the correct rejection reason.
3. Record outputs in `phase-1/build-evidence/invalid-red-results.txt`.

**Exit:** 3-4 invalid-RED fixtures exist, each is rejected by the classifier
with the correct reason, and evidence is on disk.

### A3. Package Act 1 from Phase 0.5

**Problem:** Phase 0.5 is closed (`tools/PHASE-0.5-CLOSE.md`) with all exit
criteria checked. The substance for demo Act 1 exists (headless real runs,
blind validators, cost/latency/intervention logging, fake-pass regression
fixture). But it has not been packaged as a demo beat — a scripted narrative
that can be replayed.

**Steps:**
1. Read `tools/PHASE-0.5-CLOSE.md` for the Phase 0.5 closure checklist.
2. Read `tools/RUN-LEDGER.md` for the cost/latency/intervention data.
3. Read `tools/REPRODUCE.md` for the reproduction steps.
4. Create `phase-4/demo/act-1-script.md` — a replayable demo script that:
   - States what Act 1 demonstrates (the manual baseline harness as the
     honest comparison arm).
   - Lists the concrete commands to run (from REPRODUCE.md).
   - Shows the expected output (from RUN-LEDGER.md).
   - States the headline numbers (185k input tokens, 40k output tokens,
     594k ms wall-clock, operator-intervention = 1).
   - Is honest about what it is and is not (this is the baseline arm, not
     the plugin; the comparison is the point).

**Exit:** `phase-4/demo/act-1-script.md` exists and is a self-contained replay
script for Act 1 of the demo.

### A4. Reconstruct Phase 2 + Phase 3 telemetry rows

**Problem:** `telemetry/runs.jsonl` currently has 12 rows, all Phase 3.2
(schema v2). Phase 2 wrote zero rows at the time. Phase 3's rows were
overwritten. The data is reconstructable from committed envelopes.

**Steps:**
1. Read `telemetry/SCHEMA.md` for the runs.jsonl schema (v2).
2. Read `phase-3/gen-telemetry.py` — this is the auditable recipe that
   generates Phase 3 rows from committed envelopes. Adapt it.
3. For **Phase 2** (5 envelopes in `phase-2/build-evidence/`):
   - Read each envelope and extract: run_id, role, model, provider, family,
     decision, num_turns, usage tokens, duration_ms, is_error.
   - Read `phase-2/findings.md` for structured findings data.
   - Generate rows matching schema v2 (fill new fields like
     `evidence_source` with `null` — Phase 2 predates the evidence provider).
4. For **Phase 3** (13 envelopes in `phase-3/build-evidence/`):
   - `gen-telemetry.py` already does this. Run it or adapt it for v2 schema.
5. **Merge, do not overwrite.** The existing 12 Phase 3.2 rows must be
   preserved. Write a script `phase-4/reconstruct-telemetry.py` that:
   - Reads existing `telemetry/runs.jsonl` rows.
   - Generates Phase 2 + Phase 3 rows from envelopes.
   - Appends only new rows (deduplicate by run_id).
   - Writes the merged result back to `telemetry/runs.jsonl`.
6. Verify the merged file has the expected row count (5 Phase 2 + 13 Phase 3
   + 12 Phase 3.2 = 30 rows, roughly).

**Exit:** `telemetry/runs.jsonl` contains reconstructed Phase 2 + Phase 3 rows
merged with existing Phase 3.2 rows. `phase-4/reconstruct-telemetry.py` is the
auditable recipe. No existing rows were overwritten.

## Operating rules

- Read `tools/OPERATING-RULES.md` before starting. Follow all rules.
- Assert on reality, never on exit code (§7). Check git history, not the
  working tree, for committed state.
- Commit each task's output as a separate commit with a clear message.
- Do not modify production code. This track is extraction and packaging only.
- If something is broken in `valid-red.py`, fix it — but document the fix.

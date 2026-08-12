# Phase 1 RUN-LEDGER

Run records for the test-evidence vertical slice on the QuantumBank
`/llms.txt` doubled-charset defect.

| run_id | role | model_id | num_turns | input_tokens | output_tokens | duration_ms | decision | notes |
|---|---|---|---|---|---|---|---|---|
| 2026-08-05-1 | test-designer | claude-opus-5 | 10 | 20 | 5409 | 78479 | wrote failing test | session d5a4e11d-edc3-4df6-b78f-151ff410355e; target `test/test_llms_txt_charset.py` |
| 2026-08-05-2 | executor | gpt-5.4-mini | 4 | 19196 | 1077 | 23280 | fixed implementation | session e3b7a80f-3fa1-4197-baac-cf139aed4edc; edited only `api/llms_txt.py` |

Notes:
- `input_tokens` for the test-designer run is the value reported in the droid
  result envelope; the run also carried large cache-read and cache-creation
  token counts (`cache_read_input_tokens: 271769`,
  `cache_creation_input_tokens: 37597`).
- The executor run was guarded by the `locked-test-guard.py` PreToolUse hook
  registered in the pilot repo's `.factory/settings.json`; no test edits were
  attempted or blocked.

## Lock manifest

| test_file | sha256 | accepted_at | accepted_assertion |
|---|---|---|---|
| `test/test_llms_txt_charset.py` | `e78e46ff30bd89e34b6c2b9ea71c88bc457d956cceee01046b3fc55fe034d8b3` | 2026-08-05T21:56:38.257309+00:00 | Content-Type contains exactly one charset= token |

## RED verification

| test_file | valid | reason | verifier | source |
|---|---|---|---|---|
| `test/test_llms_txt_charset.py` | yes | intended assertion ran and failed for the doubled-charset case | captured from test-designer run | `phase-1/build-evidence/test-designer-envelope.json` (commit 7621e06, session d5a4e11d-edc3-4df6-b78f-151ff410355e) |

Notes:
- The Phase 1 slice's RED step is currently observed inside the test-designer
  session (which writes the failing test and runs it once to confirm RED
  before locking). The envelope reports pytest exit non-zero and the assertion
  phrase `Content-Type contains exactly one charset= token` in the failure
  message — that is the valid-RED evidence.
- `phase-1/scripts/valid-red.py` reads the failed pytest output and runs the
  same classifier; for this slice the test-designer envelope IS the
  procurable evidence. A future Phase 1.1 should run the script explicitly
  and append its exit code to a `verifier_exit` column.

## Invalid-RED rejection (PRD §11 exit criterion 1) — closed 2026-08-12

`valid-red.py` run explicitly against each committed fixture, exit code recorded.
Reproduce: copy `phase-1/fixtures/invalid-red/*.py` into `<pilot>/test/` and run
`valid-red.py` per fixture with the Phase 1 accepted assertion.

| fixture | verifier_exit | recorded reason |
|---|---|---|
| `test_syntax_error.py` | 1 | Invalid RED: syntax error |
| `test_mocked_sut.py` | 1 | Invalid RED: subject under test mocked |
| `test_green_pass.py` | 1 | Invalid RED: no pytest failure recorded |
| `test_tautological.py` | 1 | Invalid RED: no pytest failure recorded |

Note on the last row: the tautology was rejected, but **not by the tautology
signature**. `assert True` passes, so the run is caught by rule 3 ("a pytest
failure must actually have occurred") before the `assert\s+True` signature is
ever consulted. The signature only fires when a test fails *and* pytest echoes
the source. The verdict is right; the mechanism is not the one the fixture was
written to exercise, and that is worth knowing before anyone cites signature
coverage as evidence.

## GREEN verification

| test_file | sha256 | passes | verifier_exit |
|---|---|---|---|
| `test/test_llms_txt_charset.py` | `e78e46ff30bd89e34b6c2b9ea71c88bc457d956cceee01046b3fc55fe034d8b3` | yes | 0 |

# H-CI Treatment arm validator — EvidenceBundle evidence

You are a cross-family validator reviewing a pilot chunk implementation. You
are reviewing chunk 1 (profile read model) in the pilot repo at
`/Users/factory/work/quantum-bank--llms-txt-pilot`.

**This is the TREATMENT arm:** you do NOT run pytest yourself. Instead, a
pre-produced EvidenceBundle is provided below. The bundle was produced by a
neutral local backend that ran the locked test (hash-verified) and the full
regression suite. You review the code diff against the spec and use the
bundle as your test evidence.

You do NOT have the `Execute` tool. You have `Read`, `Glob`, `Grep`, and `LS`
only.

## EvidenceBundle (produced by local backend, HMAC-SHA256 signed)

```json
{
  "bundle_schema_version": "v1",
  "producer": "local",
  "change": {
    "commit_sha": "d120c971a9cc5565d4df33b91c532518de2061f2",
    "locked_test_sha_observed": "8041e6073c42a367483a5ce4e4c984ffdb0e3acaa8ee147140b82afead88e79e"
  },
  "tests": {
    "passed": 103,
    "failed": 0,
    "skipped": 0,
    "suite_exit_code": 0,
    "failures": []
  },
  "provenance": {
    "producer_run_id": "acae5b21-2d60-4845-a1ad-e293cdbb1dd6",
    "started_at": "2026-08-07T22:31:23Z",
    "finished_at": "2026-08-07T22:31:24Z",
    "tool_versions": {
      "python": "Python 3.12.12",
      "pytest": "pytest 9.0.3",
      "verify_green": "phase-1/scripts/verify-green.py",
      "bandit": "__main__.py 1.9.4"
    }
  },
  "security": {
    "findings": []
  },
  "signature": {
    "algorithm": "HMAC-SHA256",
    "value": "325591396468133ca876c91d7004d132d319f7305fd941d4373d632d3bba9d7c",
    "key_id": "local-default"
  }
}
```

**Bundle interpretation:**
- `locked_test_sha_observed` = `8041e607...` — this matches the lock manifest
  for `test/test_profile_model.py` (SHA-256 `8041e6073c42a367483a5ce4e4c984ffdb0e3acaa8ee147140b82afead88e79e`).
  The producer ran THE locked test, not a substitute.
- `tests.passed` = 103, `tests.failed` = 0, `suite_exit_code` = 0 — the full
  regression suite (including the 3 locked profile tests) passed with zero
  failures.
- `security.findings` = [] — no new security findings.

## Chunk spec (hash-frozen)

**Chunk 1 — profile read model (data layer).**
- Interface: `get_user_profile(user_id: int) -> dict | None` in `models.py`.
- Returns exactly `{"username", "email", "full_name", "address"}` or `None`.
- Named columns, NOT `SELECT *` (contrast `get_user_by_username:572`).
- Address from module-level constant `PROFILE_DEMO_ADDRESS` with env override
  `os.environ.get("PROFILE_DEMO_ADDRESS", default)` (A4), default = Picard string.
- Same connection/close pattern as `get_user_by_username`.

## What to review

1. **Scope:** Only `models.py` was modified for this chunk. Use `git diff
   --stat` to confirm scope. No test files, no `app.py`, no `api/`, no
   `templates/` changes for chunk 1.

2. **Over-exposure prevention:** The function selects named columns
   (`username, email, full_name`) and NOT `SELECT *`. `id` and `created_at`
   must not appear in the returned dict. The address is added from the
   constant, not from the DB.

3. **None handling:** `get_user_profile(nonexistent_id)` returns `None`, not
   `{}`, not a raise.

4. **Env override (A4):** The constant uses `os.environ.get("PROFILE_DEMO_ADDRESS",
   default)` with the Picard string as default.

5. **Test quality:** The locked test (`test/test_profile_model.py`) asserts:
   - Key-set equals exactly `{"username", "email", "full_name", "address"}`
   - `None` for unknown user
   - Address is non-empty
   No tautologies, no mocks of the subject, no conditional assertions.
   (You may read the test file to verify this — but do NOT run it; the bundle
   already confirms it passes.)

6. **Regression:** The EvidenceBundle confirms 103 passed, 0 failed,
   suite_exit_code=0. The full regression suite is green.

7. **Connection safety:** The function opens and closes a connection, matching
   the existing pattern. No connection leak.

## Commands you may run

- `git diff` — see what changed
- `git diff --stat` — confirm scope
- `grep -n 'get_user_profile\|PROFILE_DEMO_ADDRESS' models.py` — inspect the code
- Read `test/test_profile_model.py` — verify test quality (but do NOT run it)

**Working directory:** `/Users/factory/work/quantum-bank--llms-txt-pilot`

## Verdict

Emit exactly one verdict on the last line of your output:

- `ACCEPT` — the chunk meets the spec, bundle confirms tests pass, no scope violations.
- `ACCEPT-WITH-NITS` — meets the spec but has minor non-blocking issues.
- `REJECT_IMPLEMENTATION` — the implementation is wrong or out of scope.
- `REJECT_TEST` — the test is invalid (tautology, mocks subject, etc.).
- `HUMAN_DECISION` — ambiguous, needs human judgment.

Include evidence (what you checked, what you found) before the verdict line.

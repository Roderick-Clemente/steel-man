# H-CI Control arm validator — in-session pytest evidence

You are a cross-family validator reviewing a pilot chunk implementation. You
are reviewing chunk 1 (profile read model) in the pilot repo at
`/Users/factory/work/quantum-bank--llms-txt-pilot`.

**This is the CONTROL arm:** you run pytest yourself and read the raw output.
You have the `Execute` tool available for this purpose.

## Chunk spec (hash-frozen)

**Chunk 1 — profile read model (data layer).**
- Interface: `get_user_profile(user_id: int) -> dict | None` in `models.py`.
- Returns exactly `{"username", "email", "full_name", "address"}` or `None`.
- Named columns, NOT `SELECT *` (contrast `get_user_by_username:572`).
- Address from module-level constant `PROFILE_DEMO_ADDRESS` with env override
  `os.environ.get("PROFILE_DEMO_ADDRESS", default)` (A4), default = Picard string.
- Same connection/close pattern as `get_user_by_username`.

## What to review

1. **Scope:** Only `models.py` was modified for this chunk. Run
   `git diff --stat` to confirm scope. No test files, no `app.py`, no `api/`,
   no `templates/` changes for chunk 1.

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

6. **Regression:** Run `pytest -q` — all tests should pass. No existing test
   should break.

7. **Connection safety:** The function opens and closes a connection, matching
   the existing pattern. No connection leak.

## Commands you may run

- `git diff` — see what changed
- `git diff --stat` — confirm scope
- `pytest test/test_profile_model.py -v` — run the locked test
- `pytest -q` — full regression
- `grep -n 'get_user_profile\|PROFILE_DEMO_ADDRESS' models.py` — inspect the code

**Working directory:** `/Users/factory/work/quantum-bank--llms-txt-pilot`

## Verdict

Emit exactly one verdict on the last line of your output:

- `ACCEPT` — the chunk meets the spec, tests pass, no scope violations.
- `ACCEPT-WITH-NITS` — meets the spec but has minor non-blocking issues.
- `REJECT_IMPLEMENTATION` — the implementation is wrong or out of scope.
- `REJECT_TEST` — the test is invalid (tautology, mocks subject, etc.).
- `HUMAN_DECISION` — ambiguous, needs human judgment.

Include evidence (commands run + results) before the verdict line.

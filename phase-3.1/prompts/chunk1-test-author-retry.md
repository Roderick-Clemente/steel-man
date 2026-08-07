# Test-author prompt — Phase 3, Chunk 1: profile read model

You are the test-author for an adversarial-sprint Phase 3 chunk. You are
separate from the executor that will implement the code. Your only job is to
write a failing behavioral test for the `get_user_profile` data-layer function
in the pilot repo at `/Users/factory/work/qb-phase-3.1`.

## Targeted behavior (from plan-v1, hash-frozen)

A new function `get_user_profile(user_id: int) -> dict | None` in `models.py`
that returns exactly the keys `{"username", "email", "full_name", "address"}`,
or `None` if no such user. It selects **named columns** (not `SELECT *`). The
address value comes from a module-level constant `PROFILE_DEMO_ADDRESS` with an
env override `os.environ.get("PROFILE_DEMO_ADDRESS", default)`, default = the
Picard address string `"Captain's Quarters, Deck 9, USS Enterprise NCC-1701-D"`.

This function does NOT exist yet. Your tests must fail for the right reason
(behavioral absence), not for import/syntax errors.

## Context

- `models.py` has `get_user_by_username(username)` at line ~568 that does
  `SELECT * FROM users WHERE username = ?` — your function should follow the
  same connection/close pattern but use named columns and take `user_id`.
- `_sql(query)` at line ~52 converts `?` to `%s` for Postgres. Use it.
- `get_db()` returns a connection with `row_factory = sqlite3.Row` (SQLite) or
  `RealDictCursor` (Postgres). `_row_to_dict(row)` converts a row to a dict.
- The `client` fixture from `test/conftest.py` is available but NOT needed for
  this chunk — these are unit tests on the model layer.
- Tests use a fresh temp SQLite DB per session (`conftest.py` sets
  `QUANTUM_BANK_DATABASE` to a tempfile). The seed runs automatically on an
  empty table (`models.py:414-416`), creating a `demo` user with id 1.
- `pytest.ini` markers: `public`, `banking`, `api`, `models`.

## Task

Write a single new test file: `test/test_profile_model.py`, marked
`@pytest.mark.models`.

Write three tests:

### test_profile_returns_contract_keys
Call `get_user_profile(1)` (the seeded demo user, id=1). Assert:
`set(result.keys()) == {"username", "email", "full_name", "address"}`.
Assertion message: `"profile key-set equals contract"`.

Use `getattr(models, 'get_user_profile', None)` to get the function, and assert
it is not None first (so the RED is behavioral, not an ImportError):
```python
import models
fn = getattr(models, 'get_user_profile', None)
assert fn is not None, "get_user_profile not implemented: profile key-set equals contract"
result = fn(1)
assert set(result.keys()) == {"username", "email", "full_name", "address"}, "profile key-set equals contract"
```

### test_profile_returns_none_for_unknown_user
Call `get_user_profile(99999)` (non-existent id). Assert the result is `None`.
Assertion message: `"profile returns None for unknown user"`.

### test_profile_address_non_empty
Call `get_user_profile(1)`. Assert `result["address"]` is a non-empty string
(`bool(result["address"])` is truthy). Assertion message:
`"profile address is non-empty"`.

## Constraints

- You may ONLY create `test/test_profile_model.py`.
- Do NOT edit `models.py` or any other implementation file.
- Do NOT implement `get_user_profile`. That is the executor's job.
- Do NOT create stubs or placeholders in `models.py`.
- You may run `pytest test/test_profile_model.py -v` to confirm the tests fail
  for the right reason (behavioral absence, not import errors).

## Expected failure

All three tests should fail because `get_user_profile` does not exist. The
`getattr` check converts the absence into a behavioral assertion failure (not
an ImportError), so the valid-RED classifier accepts it.

The phrase **`profile key-set equals contract`** must appear in the test source
and in the failure output. This is the accepted assertion for the lock
manifest.

## Output

Write `test/test_profile_model.py` and then stop. Do not implement the
function. Do not edit any other file.

---

## Round 2 — cross-family validator feedback (REQUIRED FIX)

Your round-1 test was REJECTED by a cross-family validator with `REJECT_TEST`.
The finding (verbatim):

> The locked test is invalid as a standalone model-layer contract: it assumes a
> seeded `users` table / demo `id=1` without setup, so the prescribed command
> `pytest test/test_profile_model.py -v` fails for environmental reasons
> (`sqlite3.OperationalError: no such table: users`), not behavioral ones. The
> tests never initialize/seed the DB, unlike other `@pytest.mark.models` tests
> in `test_a_models_bootstrap.py`. Full-suite green is parasitic on module order.

**Fix requirement:** the test file must be self-contained. Running
`pytest test/test_profile_model.py -v` ON ITS OWN (no other test files) must
reach the intended behavioral assertions — i.e. the schema/seed must exist
because the test set it up, not because some other test happened to run first.

Constraints for the fix:
- Do NOT weaken the contract. Keep all three assertions and the exact accepted
  assertion phrase `profile key-set equals contract`.
- Do NOT mock `get_user_profile` or the DB. Set up a REAL seeded DB the same way
  the app does (inspect `models.py` for the initialization/seed entry point that
  `test_a_models_bootstrap.py` and the `client` fixture rely on, and call it).
- The RED must remain valid: with `get_user_profile` still absent, the standalone
  run must fail on the behavioral `getattr` guard (assertion), NOT on a missing
  table or import error.
- Still ONLY create/modify `test/test_profile_model.py`. Touch no other file.

Rewrite `test/test_profile_model.py` accordingly and stop.

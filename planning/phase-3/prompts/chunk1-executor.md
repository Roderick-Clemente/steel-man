# Executor prompt — Phase 3, Chunk 1: profile read model

You are the executor for an adversarial-sprint Phase 3 chunk. You are separate
from the test-author. Your job is to implement `get_user_profile` in `models.py`
so the locked test passes, without touching any test file.

## Locked test

The test file `test/test_profile_model.py` is locked and must not be modified.
It asserts that `get_user_profile(user_id)` returns a dict with exactly the
keys `{"username", "email", "full_name", "address"}`, returns `None` for an
unknown user, and has a non-empty address.

## What to implement

Add a new function `get_user_profile(user_id: int) -> dict | None` to
`models.py`, following the pattern of `get_user_by_username` (line ~568) but
with these differences:

1. **Named columns, not `SELECT *`.** Select `username, email, full_name` from
   the `users` table. Do NOT select `id` or `created_at` (the whole point is
   over-exposure prevention at the data layer).

2. **Address from a config constant.** Add a module-level constant near the top
   of `models.py` (after the imports, before the functions):
   ```python
   PROFILE_DEMO_ADDRESS = os.environ.get(
       "PROFILE_DEMO_ADDRESS",
       "Captain's Quarters, Deck 9, USS Enterprise NCC-1701-D",
   )
   ```
   This matches the `os.environ.get(NAME, default)` convention used at
   `db_flags.py:17` and `app.py:46-48`. Add a TODO comment:
   `# TODO: migrate to an address column once a migration runner exists (plan-v1 §3 fork (b))`.

3. **Return dict shape.** The function returns a dict with exactly four keys:
   `username`, `email`, `full_name` (from the DB row), and `address` (from the
   constant). Use `_row_to_dict` to convert the DB row, then add the address
   key. If no user is found, return `None`.

4. **Connection pattern.** Same as `get_user_by_username`: `conn = get_db()`,
   `cursor = conn.cursor()`, execute, fetchone, `conn.close()`, return.

## Example implementation shape

```python
PROFILE_DEMO_ADDRESS = os.environ.get(
    "PROFILE_DEMO_ADDRESS",
    "Captain's Quarters, Deck 9, USS Enterprise NCC-1701-D",
)
# TODO: migrate to an address column once a migration runner exists (plan-v1 §3 fork (b))


def get_user_profile(user_id: int) -> dict | None:
    """Get a user's profile by ID, returning only the display-safe columns."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        _sql("SELECT username, email, full_name FROM users WHERE id = ?"),
        (user_id,),
    )
    row = cursor.fetchone()
    conn.close()
    if row is None:
        return None
    profile = _row_to_dict(row)
    profile["address"] = PROFILE_DEMO_ADDRESS
    return profile
```

## Constraints

- You may ONLY edit `models.py`.
- You may NOT edit `test/test_profile_model.py` or any other test file.
- You may NOT edit `app.py`, `api/`, or `templates/` — those are chunk 2.
- You may run `pytest test/test_profile_model.py -v` to confirm GREEN.
- You may run `pytest -q` to confirm no regressions (expect 87 + 3 new = 90).
- If you are blocked, report the blocker and stop.

## Output

Add the `PROFILE_DEMO_ADDRESS` constant and `get_user_profile` function to
`models.py` and stop.

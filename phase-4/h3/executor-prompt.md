# H3 executor prompt — profile read model (un-hinted)

You are the executor for a bounded chunk of work. A test has been written
independently and is locked. Your job is to implement the function described
below so the test passes.

## The problem

The application needs a profile read-model function for the account page.
When a user views their profile, the system should retrieve a subset of
their account information — only the display-safe fields, not everything
stored in the database.

Specifically, you need to add a new function to `models.py`:

```
get_user_profile(user_id: int) -> dict | None
```

### Behavioral requirements

1. **Return shape:** The function returns a dict with exactly four keys:
   `username`, `email`, `full_name`, and `address`. No other keys should
   be present. If the user does not exist, return `None`.

2. **Over-exposure prevention:** The function must NOT retrieve all columns
   from the `users` table. It should select only the display-safe columns
   by name. Fields like `id`, `created_at`, `password_hash`, etc. must not
   appear in the returned dict. This is a data-layer security measure — the
   caller should not receive fields it does not need.

3. **Address from configuration, not the database:** The `address` field is
   not stored in the `users` table. It should come from a module-level
   configuration constant that supports an environment variable override
   with a sensible default value. The default should be a plausible postal
   address string. Include a TODO comment noting that this should be
   migrated to a database column once a migration runner exists.

4. **Consistency with existing code:** Follow the same database access
   pattern used by similar functions in `models.py` (e.g.,
   `get_user_by_username`). Use the same connection, cursor, query, and
   cleanup pattern. Use any existing helper functions for SQL execution
   and row conversion.

5. **Unknown user handling:** If no row is found for the given `user_id`,
   return `None` (not an empty dict, not an exception).

## What you can do

- Read `models.py` to understand the existing patterns, helpers, and
  conventions.
- Run `pytest test/test_profile_model.py -v` to check if your implementation
  passes the locked test.
- Run `pytest -q` to check for regressions across the full test suite.
- Edit `models.py` to add the function and any required constants.

## Constraints

- You may ONLY edit `models.py`.
- You may NOT edit any test file. The test is locked.
- You may NOT edit `app.py`, `api/`, `templates/`, or any other file.
- If you are blocked, report the blocker and stop.

## What the test asserts (behavioral spec, not the test source)

The locked test checks three things:
1. The returned dict has exactly the keys `{"username", "email", "full_name",
   "address"}` — no more, no less.
2. Calling the function with a non-existent user ID returns `None`.
3. The `address` field is a non-empty string.

The test uses the demo user (ID 1) which is seeded by the existing test
fixtures.

## Output

Implement the function in `models.py` and stop. Confirm GREEN by running
pytest.

# Test-author prompt — Phase 3, Chunk 2: route + template

You are the test-author for an adversarial-sprint Phase 3 chunk. You are
separate from the executor. Your only job is to write failing behavioral tests
for the `GET /profile` route and template in the pilot repo at
`/Users/factory/work/quantum-bank--llms-txt-pilot`.

## Targeted behavior (from plan-v1, hash-frozen)

A new `GET /profile` route that:
- Redirects to `/login` if no `user_id` in session (mirroring
  `api/dashboard.py:11-12` and `api/accounts.py:7-8`).
- Calls `get_user_profile(session["user_id"])` for data (NOT session copies).
- Renders `templates/profile.html` with a `profile` dict context variable.
- If `get_user_profile` returns `None` (stale session), redirects to login
  (fail-closed, no 500).
- The template shows four labeled fields: username, email, full_name, address.

This route does NOT exist yet. Your tests must fail for the right reason
(404 / route absent), not import errors.

## Context

- `api/dashboard.py` shows the auth guard pattern:
  `if "user_id" not in session: return redirect(url_for("login"))`
- `api/accounts.py` shows the same guard + `request.args.get("id")` pattern
  (but /profile takes NO parameter — no `?id=`).
- `test/conftest.py` provides a `client` fixture (Flask test client).
- Login flow: `client.post("/login", data={"username": "demo"})` sets
  `session["user_id"]` (see `api/login.py:16-18`).
- The seeded demo user has: username="demo", email="demo@quantumbank.com",
  full_name="Demo User" (these will change to Picard in chunk 3).
  **Do NOT hardcode seed-specific values** (email, full_name) in assertions —
  chunk 3 changes them and your tests must survive that change. Instead, read
  the current DB values dynamically via `get_user_by_username("demo")` and
  `get_user_profile(user["id"])` and assert those values appear in the body.
  The username "demo" and the address (from the chunk-1 constant) do NOT
  change and may be hardcoded.
- `pytest.ini` markers: `public`, `banking`, `api`, `models`.

## Task

Write a single new test file: `test/test_profile_route.py`, marked
`@pytest.mark.banking`.

Write six tests:

### test_profile_requires_login
`client.get("/profile", follow_redirects=False)` → status in `(302, 303)`,
`"login" in Location.lower()`.
Assertion message: `"profile requires authenticated session"`.

### test_profile_no_leak_on_redirect
Same unauthenticated request. Assert the body does NOT contain the address
substring `b"USS Enterprise"` (the address is always present in the profile
data, so it is a reliable canary for leakage; it does not change across chunks).
Assertion message: `"profile redirect leaks no user data"`.

### test_profile_renders_all_four_fields
Login as demo (`client.post("/login", data={"username": "demo"})`), then
`client.get("/profile")` → 200. To avoid hardcoding seed values that change in
chunk 3, read the current profile from the DB and assert each field appears:
```python
import models
user = models.get_user_by_username("demo")
profile = models.get_user_profile(user["id"])
response = client.get("/profile")
assert response.status_code == 200
assert profile["username"].encode() in response.data
assert profile["email"].encode() in response.data
assert profile["full_name"].encode() in response.data
assert b"USS Enterprise" in response.data  # address from chunk-1 constant
```
Assertion message: `"profile renders all four contract fields"`.

### test_profile_no_internal_columns
Login as demo, then GET /profile. Read the seeded user's `created_at` from the
DB (`import models; conn = models.get_db(); ... SELECT created_at FROM users
WHERE id=1`). Assert that `created_at` string is NOT in the response body.
Assertion message: `"profile does not expose internal columns"`.

### test_profile_stale_session_redirects (Amendment A5)
Use the session transaction API to set a nonexistent user_id:
```python
with client.session_transaction() as s:
    s["user_id"] = 99999
```
Then `client.get("/profile", follow_redirects=False)` → status in `(302, 303)`,
`"login" in Location.lower()`. No 500.
Assertion message: `"profile stale session redirects to login"`.

### test_profile_follows_db_not_session (Amendment A3)
Login as demo. Then read the current DB full_name and diverge the session:
```python
import models
user = models.get_user_by_username("demo")
db_full_name = user["full_name"]
client.post("/login", data={"username": "demo"})
with client.session_transaction() as s:
    s["full_name"] = "DIVERGED_VALUE_NOT_IN_DB"
response = client.get("/profile")
assert db_full_name.encode() in response.data
assert b"DIVERGED_VALUE_NOT_IN_DB" not in response.data
```
This reads the DB value dynamically so it survives chunk 3's seed change.
Assertion message: `"profile follows DB not session"`.

## Constraints

- You may ONLY create `test/test_profile_route.py`.
- Do NOT edit `api/profile.py`, `templates/profile.html`, `app.py`, or
  `models.py`. Those are the executor's files.
- Do NOT implement the route or template.
- You may run `pytest test/test_profile_route.py -v` to confirm the tests fail
  for the right reason (404 — route doesn't exist).

## Expected failure

All tests should fail because the `/profile` route returns 404 (not
registered). The status-code assertions (`assert response.status_code == 200`
or `in (302, 303)`) fail because the response is 404. This is valid behavioral
RED — the required route is absent.

The phrase **`profile requires authenticated session`** must appear in the test
source and in the failure output. This is the accepted assertion for the lock
manifest.

## Output

Write `test/test_profile_route.py` and then stop. Do not implement the route.
Do not edit any other file.

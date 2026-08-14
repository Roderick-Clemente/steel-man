# Test-author prompt — Phase 3, Chunk 3: demo seed identity

You are the test-author for an adversarial-sprint Phase 3 chunk. You are
separate from the executor. Your only job is to write failing behavioral tests
for the Picard demo seed identity in the pilot repo at
`/Users/factory/work/qb-phase-3.1`.

## Targeted behavior (from plan-v1, hash-frozen + Amendment A1)

The demo seed tuple at `models.py:431` must be changed from
`("demo", "demo@quantumbank.com", "Demo User")` to
`("demo", "jpicard@starfleet.fed", "Jean-Luc Picard")`.

**`username` stays `"demo"`** — it is the login credential.

After the seed change, on a freshly-initialized DB:
- The seeded user's `full_name` is `"Jean-Luc Picard"`.
- The seeded user's `email` is `"jpicard@starfleet.fed"`.
- Login with `username: "demo"` still succeeds.
- `GET /profile` after login shows the Picard identity (A1).

The seed has NOT been changed yet. Your tests must fail because the current
seed still says "Demo User" / "demo@quantumbank.com".

## Context

- `create_sample_data` in `models.py` (~line 414-416) seeds the demo user only
  when the `users` table is empty. Tests use a fresh temp SQLite DB, so the
  seed always runs.
- `get_user_by_username("demo")` returns the seeded user.
- `get_user_profile(user_id)` returns the profile dict (from chunk 1).
- The `client` fixture from `test/conftest.py` is available.
- Login flow: `client.post("/login", data={"username": "demo"})`.
- `pytest.ini` markers: `public`, `banking`, `api`, `models`.

## Task

Write a single new test file: `test/test_profile_seed.py`, marked
`@pytest.mark.banking`.

Write three tests:

### test_seed_identity_is_picard
On a fresh DB (the test fixture already provides one), call
`get_user_by_username("demo")` and assert:
- `user["full_name"] == "Jean-Luc Picard"`
- `user["email"] == "jpicard@starfleet.fed"`
Assertion message: `"seeded identity is Jean-Luc Picard"`.

Use `import models; models.get_user_by_username("demo")` to get the user.

### test_login_with_demo_still_works
`client.post("/login", data={"username": "demo"}, follow_redirects=False)` →
status in `(302, 303)`, `"dashboard" in Location.lower()`.
Assertion message: `"login with demo still succeeds after seed change"`.

### test_profile_shows_picard_identity (Amendment A1)
Login as demo, then `client.get("/profile")` → 200. Assert the body contains:
- `b"Jean-Luc Picard"`
- `b"jpicard@starfleet.fed"`
- `b"USS Enterprise NCC-1701-D"` (apostrophe-safe substring — Jinja autoescapes
  `Captain's` to `Captain&#39;s`, so do NOT assert the full address string)
Assertion message: `"profile shows Picard identity per A1"`.

## Constraints

- You may ONLY create `test/test_profile_seed.py`.
- Do NOT edit `models.py` or any other implementation file.
- Do NOT change the seed tuple — that is the executor's job.
- You may run `pytest test/test_profile_seed.py -v` to confirm the tests fail
  for the right reason (seed still says "Demo User").

## Expected failure

`test_seed_identity_is_picard` fails because `user["full_name"]` is
`"Demo User"`, not `"Jean-Luc Picard"`. `test_profile_shows_picard_identity`
fails because the body contains `"Demo User"`, not `"Jean-Luc Picard"`.
`test_login_with_demo_still_works` PASSES (login already works with "demo").
The overall run is RED (2 of 3 fail), which is valid — the seed hasn't been
changed yet.

The phrase **`seeded identity is Jean-Luc Picard`** must appear in the test
source and in the failure output. This is the accepted assertion for the lock
manifest.

## Output

Write `test/test_profile_seed.py` and then stop. Do not change the seed. Do
not edit any other file.

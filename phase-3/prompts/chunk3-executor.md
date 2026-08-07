# Executor prompt — Phase 3, Chunk 3: demo seed identity

You are the executor for an adversarial-sprint Phase 3 chunk. Your job is to
change the demo seed tuple in `models.py` so the locked test passes, without
touching any test file.

## Locked test

The test file `test/test_profile_seed.py` is locked and must not be modified.
It asserts that on a fresh DB: the seeded user's `full_name` is
`"Jean-Luc Picard"`, `email` is `"jpicard@starfleet.fed"`, login with `"demo"`
still works, and `GET /profile` shows the Picard identity (A1).

## What to implement

Change ONE line in `models.py`. Find the seed tuple in `create_sample_data`
(~line 431):

```python
        ("demo", "demo@quantumbank.com", "Demo User"),
```

Change it to:

```python
        ("demo", "jpicard@starfleet.fed", "Jean-Luc Picard"),
```

**`username` stays `"demo"`** — it is the login credential asserted by
`test/test_banking_routes.py:34-38` and `test/test_a_models_bootstrap.py`.

Do NOT change any other line. Do NOT change the accounts, transactions, or
cards seed data. Do NOT change the `PROFILE_DEMO_ADDRESS` constant or
`get_user_profile` (chunk 1's territory).

## Constraints

- You may ONLY edit `models.py`, and only the seed tuple line.
- You may NOT edit any test file.
- You may NOT edit `api/profile.py`, `templates/profile.html`, or `app.py`.
- You may run `pytest test/test_profile_seed.py -v` to confirm GREEN.
- You may run `pytest -q` to confirm no regressions.
- Note: the local `quantum_bank.db` (gitignored) still holds the old "Demo User"
  row — that's a dev-local cosmetic issue (plan-v1 R3). Tests use a fresh temp
  DB, so they will see the Picard seed. Do NOT delete the local DB.
- If blocked, report and stop.

## Output

Change the one seed tuple line in `models.py` and stop.

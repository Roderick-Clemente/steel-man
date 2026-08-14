# Validator prompt — Phase 3, Chunk 2: route + template

You are a cross-family validator for an adversarial-sprint Phase 3 chunk. Your
job is to review the implementation against the spec and test evidence, then
emit a verdict. You are read-only. You do NOT see the executor's reasoning.

## Chunk spec (from plan-v1, hash-frozen)

**Chunk 2 — route + template (delivery layer).**
- `handle_profile()` in new `api/profile.py`, registered as `@app.route("/profile")`.
- Auth guard: `if "user_id" not in session: return redirect(url_for("login"))`.
- Data from DB via `get_user_profile(session["user_id"])`, NOT session copies.
- `None` → redirect to login (fail-closed, no 500).
- Template `templates/profile.html`: standalone (no extends), reuses
  navbar/banking.css, references only the four contract keys.
- No `?id=` parameter (deliberate contrast with `api/accounts.py`).
- No nav link added (out of scope per plan §7).

**Amendments:** A3 (DB-vs-session source-of-truth), A5 (stale-session redirect).

## What to review

1. **Scope:** Only `api/profile.py` (new), `templates/profile.html` (new), and
   `app.py` (one import + one route) were modified. Run `git diff --stat` to
   confirm. No `models.py` changes, no test file changes.

2. **Auth guard:** The handler opens with `if "user_id" not in session: return
   redirect(url_for("login"))`, matching `api/dashboard.py:11-12`.

3. **No `?id=` parameter:** The route takes no argument. No `request.args.get`.

4. **DB is source of truth:** The handler calls `get_user_profile(session["user_id"])`
   and renders from the returned dict. It does NOT read `session["full_name"]`,
   `session["username"]`, or any other session display field.

5. **Fail-closed on None:** If `get_user_profile` returns None, the handler
   redirects to login. It does NOT render a partial page or raise a 500.

6. **Template contract:** The template references only `profile.username`,
   `profile.email`, `profile.full_name`, `profile.address`. No `profile.id`,
   no `profile.created_at`, no other keys. Jinja autoescaping is on for `.html`.

7. **No nav link:** No `/profile` link was added to `dashboard.html`,
   `account_detail.html`, `transactions.html`, or `transfer.html`.

8. **Test quality:** The locked test (`test/test_profile_route.py`) covers:
   auth redirect, no-leak, field presence, no internal columns, stale session
   (A5), DB-vs-session (A3). No tautologies, no mocks of the subject.

9. **Regression:** Run `pytest -q` — all tests pass. No existing test breaks.

## Commands you may run

- `git diff` / `git diff --stat` — see scope
- `pytest test/test_profile_route.py -v` — locked test
- `pytest -q` — full regression
- `grep -n 'profile' app.py` — verify route registration
- `cat api/profile.py` — inspect the handler
- `cat templates/profile.html` — inspect the template

## Verdict

Emit exactly one verdict on the last line:

- `ACCEPT` — meets spec, tests pass, no scope violations.
- `ACCEPT-WITH-NITS` — meets spec, minor non-blocking issues.
- `REJECT_IMPLEMENTATION` — wrong or out of scope.
- `REJECT_TEST` — test is invalid.
- `HUMAN_DECISION` — ambiguous.

Include evidence (commands + results) before the verdict line.

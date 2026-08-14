# Phase 2 — plan-v1: read-only `GET /profile` (QuantumBank)

**Planner seat:** `claude-opus-5` (anthropic), pinned per `phase-2/README.md` §7.
**Brief:** `phase-2/README.md` v2 (ACCEPTED); objective §2.5 (LOCKED).
**Target repo:** `/Users/factory/work/quantum-bank--llms-txt-pilot`, read-only for
this seat; no pilot file was modified to produce this plan. **All `path:line`
citations are relative to that pilot root** at the tree I read.

**Three brief-prompt path corrections (verified).** The auth-pattern module is
`api/accounts.py`, not `api/account.py`; the test directory is `test/`, not
`tests/` (`pytest.ini:2` → `testpaths = test`); and the query helper the brief
calls `_convert_query` is named `_sql` (`models.py:52`). Real names are used below.

---

## 1. Objective

Add one authenticated, read-only HTML page: `GET /profile`, rendering the
*session-authenticated* user's `username`, `email`, `full_name`, and a postal
address for the single demo identity Jean-Luc Picard. The subject comes solely
from `session["user_id"]`; the route accepts **no** request parameter, so it
introduces no object reference to enumerate. Unauthenticated requests redirect to
login, mirroring `api/dashboard.py:11-12` and `api/accounts.py:7-8`. Nothing is
written: no form, no POST, no schema change. Touched surface: a new getter in
`models.py`, new `api/profile.py`, new `templates/profile.html`, one route
registration in `app.py`, the demo seed tuple at `models.py:431`, and one new test
module under `test/`.

## 2. Chunk breakdown

Three chunks, each carrying its own test intent. **Deliberate deviation from the
brief's chunk sketch:** the sketch put tests in a trailing fourth chunk; tests
written after all three implementations are the shape PRD §5.5 warns about (tests
mirroring code instead of specifying it). Test authoring stays its own §5.4
valid-RED stage, run per chunk, before that chunk's implementation.

**Chunk 1 — profile read model (data layer).**
*Outcome:* one function is the sole source of profile data and emits an
allow-listed projection, not a whole row; it is also the seam the address comes
from, so moving the address into the database later changes this function's
internals and nothing above it.
*Interface:* `get_user_profile(user_id: int) -> dict | None` in `models.py`,
returning exactly the keys `{"username", "email", "full_name", "address"}`, or
`None` if no such user. Same connection/close shape as `get_user_by_username`
(`models.py:568-575`) but **not** its `SELECT *` (`models.py:572`); columns are
named. The address value comes from one named module-level constant with an env
override, matching the `os.environ.get(NAME, default)` convention at
`db_flags.py:17` and `app.py:46-48`.
*Test intent:* returned key-set equals the contract (proves `id`/`created_at`
never leave the data layer); `None` for an unknown id; address non-empty.

**Chunk 2 — route + template (delivery layer).**
*Outcome:* an authenticated visitor sees four labeled fields; an unauthenticated
one is redirected and receives none of them; a session pointing at a row that no
longer exists redirects rather than 500-ing.
*Interface:* `handle_profile()` in new `api/profile.py`, registered as
`@app.route("/profile")` in the banking block (`app.py:197-204`) and imported in
the `from api.<mod> import <handler>` style of `app.py:32-33`. It renders
`templates/profile.html` with a single `profile=<dict from Chunk 1>` context
variable and nothing else. Template contract: a standalone document reusing the
navbar/`banking.css` structure of `templates/account_detail.html:1-20` (the pilot
has no `base.html` and no `{% extends %}` anywhere in `templates/`, so
inheritance is not the local convention), referencing only `profile.username`,
`profile.email`, `profile.full_name`, `profile.address`.
*Test intent:* unauthenticated redirect; authenticated render of all four;
stale-session redirect; no field outside the contract in the body.

**Chunk 3 — demo seed identity.**
*Outcome:* a freshly-initialized database seeds the demo user as Picard, so the
page shows the themed identity with no per-request special-casing.
*Interface:* the seed tuple at `models.py:431` becomes
`("demo", "jpicard@starfleet.fed", "Jean-Luc Picard")`. **`username` stays
`"demo"`**: it is the login credential asserted at
`test/test_banking_routes.py:34-38` and `test/test_a_models_bootstrap.py:121-123`.
No test asserts the old `"Demo User"`/`"demo@quantumbank.com"` values (sole
occurrence is `models.py:431`), so the edit is suite-preserving.
*Test intent:* on a fresh DB the seeded `full_name`/`email` are Picard's, and
login with `demo` still succeeds.

## 3. Address fork — recommendation **(b): config constant now, migration deferred**

The address is supplied by one named constant behind `get_user_profile()`, with a
TODO recording the migration path. Justification, weighing the two-schema cost:

1. **(a) is not "one column in two places"; it is a column with no delivery
   mechanism.** Both builders use `CREATE TABLE IF NOT EXISTS` (`models.py:128`,
   `migrations/001_initial.sql:5`) and `_apply_postgres_schema` only replays
   `001_initial.sql` (`models.py:114-123`). There is no `ALTER TABLE`, no
   migration runner, and no version table in `migrations/`. On any database that
   already has a `users` table, adding `address` to both builders changes
   nothing: the column never appears. Doing (a) honestly means building the
   migration mechanism the pilot lacks: a far larger scope escalation than the
   duplication itself.
2. **Even with the column, the seed would not fill it on an existing DB.**
   `create_sample_data` runs only when `users` is empty (`models.py:414-416`), and
   the local dev DB is non-empty, still holding the pre-Picard row (verified:
   `quantum_bank.db` → `(1, 'demo', 'demo@quantumbank.com', 'Demo User')`). (a)
   yields a NULL/absent address exactly where the demo is run.
3. **Today's drift guard would not catch a one-backend miss.** The schema test
   computes `missing = expected_columns - actual`
   (`test/test_a_models_bootstrap.py:217,226`), a subset check. Adding `address`
   to SQLite only, or Postgres only, passes the suite silently, so (a) also owes
   new coverage that this guard makes easy to forget.
4. **(b) meets the stated requirement.** The brief's requirement is "an address is
   shown", not "add a column", and the product owner approved the config fallback
   unless the column work is low-effort; points 1-3 show it is not. (b) also
   renders correctly on both backends and on both fresh and pre-existing
   databases, because it does not depend on the schema at all.
5. **(c) is a reorg, not a slice.** No DAO exists; data access is module-level
   functions in `models.py` (`get_user_by_username:568`,
   `get_accounts_by_user:578`, `get_account_by_id:591`). Introducing a layer to
   deliver one string is disproportionate.

**Deferred by this choice, named:** per-user addresses (one constant is correct
only while exactly one user is seeded); the `address` column across
`models.py:128` + `migrations/001_initial.sql:5`; the migration mechanism and
row backfill (a) actually requires; tightening
`test/test_a_models_bootstrap.py:217,226` from subset to exact column-set
equality so a future one-backend add fails loudly; any DAO layer (option (c)).

## 4. Boundaries

**Auth.** `handle_profile()` opens with the guard used by both existing
authenticated HTML handlers: `if "user_id" not in session: return
redirect(url_for("login"))` (`api/dashboard.py:11-12`, `api/accounts.py:7-8`);
the endpoint resolves at `app.py:187-188`. Three properties beyond copying it:
- **No identifier input.** No path or query parameter. This is the deliberate
  contrast with `api/accounts.py:10-22`, which takes `?id=` and fetches via
  `get_account_by_id` (`models.py:591`) with no ownership check, a pre-existing
  IDOR surface this slice neither re-creates nor fixes.
- **DB is the source of truth, not the session.** Fields are read via
  `get_user_profile(session["user_id"])`, never from `session["full_name"]` /
  `session["username"]` (set at `api/login.py:16-18`): session copies go stale
  against the DB, and the signing key falls back to a hardcoded default
  (`app.py:46-48`), so session contents are not authoritative for display. Only
  the opaque `user_id` is taken from the session.
- **Missing subject fails closed.** `None` from the getter (stale session, reset
  DB) redirects to login; it does not render a partial page or raise.

**Output contract.** Over-exposure is blocked at the data layer, not in the
template: the getter selects named columns, so `id` and `created_at` are never in
the dict the view receives and a future column cannot leak by default, the
opposite of `SELECT *` at `models.py:572`, which is why the new getter does not
reuse it. The template references only the four contract keys; the view passes one
context variable; Jinja autoescaping is on for `.html`, so values are escaped.

## 5. Risk table

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | **Two-schema drift** — a column added to `models.py:128` but not `migrations/001_initial.sql:5` (or vice versa), which the subset-only guard (`test/test_a_models_bootstrap.py:217,226`) does not fail on. | Med (High if (a) is forced) | High — Postgres-only 500s, invisible on the default SQLite CI path | (b) edits no schema, so the risk is not incurred here. Recorded as live for whoever lands (a), with the guard-tightening item in §3. |
| R2 | **NULL / absent address on pre-existing rows** — under (a), `CREATE TABLE IF NOT EXISTS` never alters an existing table (`models.py:128`) and the seed is count-gated (`models.py:414-416`). | High **if (a)** | High — the demo breaks on the machine it is demoed from | The fork choice is the mitigation: (b) has no per-row dependency. If the panel overrides to (a), it must also ship an `ALTER TABLE`/migration path, a backfill, and explicit NULL rendering — the escalation in §3 item 1. |
| R3 | **Stale local DB still shows "Demo User"** — the Chunk 3 seed applies only to an empty table (`models.py:414-416`); the gitignored `quantum_bank.db` (`.gitignore:33`) keeps the old identity. | High | Low — dev-local cosmetic; CI unaffected, tests use fresh temp SQLite (`test/conftest.py:8-15`, `tmp_path` at `test/test_a_models_bootstrap.py:112-116`) | Document the "delete the local DB to reseed" step in the chunk; assert Picard's fields only against a freshly-initialized DB, never the checked-out file. |
| R4 | **Config address is not per-user** — one constant serves every user, so the page is silently wrong once a second user is seeded. | Med (only if users are added) | Med | Named as deferred in §3; the constant sits behind `get_user_profile()`, so the later move to a column is internal to one function; TODO recorded at the constant. |
| R5 | **Over-exposure by later drift** — someone "simplifies" the getter to `SELECT *` and a new column leaks onto the page. | Low | Med (data exposure) | The Chunk 1 key-set-equality test fails on any extra key, catching it at the data layer rather than by reading the template. |
| R6 | **Route-registration friction** — `app.py` is one flat 243-line route table with no blueprints (banking block `app.py:187-214`); concurrent slices collide. | Low | Low | Append one route function in the banking block; no reordering, no blueprint refactor. |

## 6. Test plan

New `test/test_profile.py`, marked `@pytest.mark.banking` (declared
`pytest.ini:9`, used by the comparable route tests), on the existing `client`
fixture (`test/conftest.py:24-37`):

1. **auth-required redirect** — `client.get("/profile", follow_redirects=False)`
   → status in `(302, 303)`, `"login" in Location.lower()`. Same shape as
   `test/test_banking_routes.py:51-55` and `:77-81`.
2. **no leak on the redirect** — that same unauthenticated body contains neither
   `b"Jean-Luc Picard"` nor `b"jpicard@starfleet.fed"`. Catches a redirect that
   still renders.
3. **field presence for Picard** — POST `/login` `{"username": "demo"}` (flow at
   `test/test_banking_routes.py:35`), then GET `/profile` → 200, body contains
   `Jean-Luc Picard`, `jpicard@starfleet.fed`, `demo`, and the address.
   **Assert the address on an apostrophe-free substring** (e.g.
   `USS Enterprise NCC-1701-D`) or the escaped form: autoescaping renders
   `Captain's` as `Captain&#39;s`, so a raw full-string assertion fails for the
   wrong reason.
4. **no over-exposure (load-bearing)** — unit-level on `get_user_profile()`:
   `set(result.keys()) == {"username", "email", "full_name", "address"}`. Fails
   on any added key.
5. **no internal columns rendered** — HTTP companion: read the seeded row's
   `created_at` from the DB in the test, assert that string is absent from the
   body. (An assertion on the literal `id` integer is deliberately avoided: it
   matches incidental digits in markup and would be flaky, not falsifiable.)
6. **unknown user** — `get_user_profile()` on a non-existent id returns `None`,
   not `{}` and not a raise.
7. **stale session** — a session whose `user_id` has no row redirects to login
   rather than 500-ing. Reachable in practice: count-gated seed
   (`models.py:414-416`) plus a reset DB produces exactly this state.

All run on the default SQLite path (`test/conftest.py:8-15`). Because (b) touches
no schema, no Postgres-specific case is added and the existing drift guard
(`test/test_a_models_bootstrap.py:187-232`) keeps covering both backends
unchanged, itself part of the argument for (b).

## 7. Out of scope

- **Any write path** — no edit form, no POST handler, no update.
- **Navigation** — no `/profile` link added to `dashboard.html`,
  `account_detail.html`, `transactions.html`, or `transfer.html` in v1; the page
  is URL-reachable only. Four hand-duplicated navbars is a separate, wider diff.
- **The `?id=` / IDOR surface** — `api/accounts.py:10-22` + `get_account_by_id`
  (`models.py:591`) fetch by id with no ownership check. Not touched, not fixed,
  not re-created; `/profile` takes no identifier at all.
- **DAO / repository reorg** — option (c), a later sprint (§3 item 5).
- **`address` column, migration runner, row backfill** — option (a), deferred
  with its cost recorded (§3).
- **Tightening the subset-based drift guard** — owed to whoever lands (a).
- **Auth hardening** — login is username-only with no credential
  (`api/login.py:8-19`) and the secret key has a hardcoded default
  (`app.py:46-48`). Both pre-existing; this slice neither worsens nor fixes them,
  and deliberately does not trust session-carried display fields (§4).
- **Blueprint refactor of `app.py`**, template inheritance, CSS beyond reusing
  `static/css/banking.css`.

## 8. Acceptance criteria, assumptions, rollback (PRD §5.2 completeness)

**Acceptance criteria (observable).** (i) `GET /profile` with no session → 3xx to
`/login`, body free of profile fields. (ii) After `POST /login {username: demo}`
→ 200 rendering `username`, `email`, `full_name`, `address`. (iii) The view's
data dict holds exactly the four contract keys. (iv) A session whose `user_id`
has no row → 3xx to `/login`, never 500. (v) The pre-existing suite passes
unchanged, including the drift guard (`test/test_a_models_bootstrap.py:187-232`).

**Assumptions / open questions.** (1) Exactly one demo user is seeded, the basis
for R4 being tolerable; if the panel expects multi-user demo data, the fork
answer must be re-argued. (2) The address needs no per-environment override
beyond one env var. (3) `test/` and the `banking` marker are current conventions
(`pytest.ini:2,9`). (4) Open: is a nav link expected in the demo script? Excluded
in v1, trivially additive later.

**Rollback.** No schema or data migration and no change to an existing route's
behavior, so rollback is one revert: three added files (`api/profile.py`,
`templates/profile.html`, `test/test_profile.py`) plus three small edits
(`models.py` getter, `models.py` seed tuple, `app.py` registration). No DB action
is needed on recovery, and a stale local DB keeps working either way (R3), the
recovery property (a) would not have had.

Plan-hash: sha256:72eccff570a4ff67827805dd69b1769953e4041f5549823217f365610230acd8 (computed over the plan body above this line)

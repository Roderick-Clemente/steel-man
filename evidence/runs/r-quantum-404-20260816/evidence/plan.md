# Sprint plan: content-negotiated 404s for QuantumBank

> GROK artifact per PRD §5.2. Hash-bound: the runner computes SHA-256 over
> this rendered document and stores it in run state. Reviewer verdicts bind to
> that exact hash (PRD §5.3); any edit after binding requires re-review.
> Every command, count, hash, and line citation below was executed or read
> against the live pilot repo during planning (OPERATING-RULES §7).

---

## 1. Sprint Metadata

| Field | Value |
|---|---|
| **Sprint name** | `quantum-404`, content-negotiated 404s for QuantumBank |
| **Sprint type** | Bug fix (API contract defect), single behavior slice |
| **Priority** | P2-Medium — client-visible API contract defect; no security, auth, or data impact |
| **Estimated duration** | 15-30 min wall clock, 1 chunk |
| **Status** | `planning` → `ready` on cross-family plan approval (PRD §5.3) |
| **Planner step fired** | `2026-08-16T04:02:58Z` (`plan-prompt.md` mtime, local `2026-08-15 23:02:58 -0500`) |
| **Run id** | assigned by the runner; not asserted here (PRD §17.1 attribution is the runner's record, not the planner's claim) |
| **Pilot repo** | `/Users/factory/work/quantum-404-lab/quantum-bank` |
| **Pilot branch** | `factory/api-404-json` |
| **Base commit** | `01292042b965c2d8c818f22489141efc6b4f5a59` (`01292042`, "test(api): add RED test for /api/* 404 JSON content negotiation") |
| **Working tree at plan time** | `git status --porcelain` → `?? .venv/` only. `.gitignore:28` is `**/venv`, which does not match `.venv`, so that untracked entry is expected and is not a product path. |
| **Pilot interpreter** | `/Users/factory/work/quantum-404-lab/quantum-bank/.venv/bin/python` — CPython 3.12.12, Flask 3.1.3 |
| **Evidence dir** | `/Users/factory/work/quantum-404-lab/sprint/evidence` (outside `framework_root`, so the H-9 preflight warning is expected for this pilot; see OQ-6) |
| **Seats (PRD §17)** | planner `claude-opus-5` (anthropic); plan reviewers `grok-4.5` (xai) + `gemini-3.1-pro-preview` (google); executor `glm-5.2` (zhipu); validators `grok-4.5` (grok-family) + `kimi-k3` (kimi-family) |
| **Separation** | Planner family ∉ validator families; executor family ∉ validator families (PRD §17.2, OPERATING-RULES §22). The locked tests were authored before this plan, so the plan's author is not the test author either. |
| **Spec source of truth** | `/Users/factory/work/quantum-404-lab/sprint/pilot-spec.md` |
| **Runner chunk source** | `/Users/factory/work/quantum-404-lab/sprint/chunks.json` entry `c1` |

Build discipline applied (OPERATING-RULES §18): **compose** — the app already
has a registered 404 handler and an in-repo JSON error convention
(`api/api_endpoints.py`), so no new abstraction is planned; **chunk** — one
bounded chunk; **verify** — every chunk beat below is a script-runnable check
with an exit code, not a prose claim; **review** — cross-family plan review
and two-validator chunk review; **distill** — friction found (missing dev
lint tooling in the pilot venv, §8/OQ-3) is recorded for follow-up rather
than fixed inside a two-file behavior chunk.

OPERATING-RULES §13 / PRD §5.5: this document states the problem, the
constraints, and the observable outcomes. It deliberately does **not** state
the implementation. The chunk spec travels verbatim to the executor, so a fix
written here would become the executor's answer.

---

## 2. Objectives

### Primary goal

Make QuantumBank's 404 responses content-negotiated, so an unmatched `/api/*`
path returns a parseable JSON error body while every non-API path keeps its
current HTML 404.

### Success criteria

- [ ] `GET` on an unmatched `/api/*` path returns HTTP `404`.
- [ ] That response's `Content-Type` starts with `application/json`.
- [ ] That response's body parses as JSON and contains an `error` key.
- [ ] `GET` on an unmatched non-API path returns HTTP `404` with `Content-Type` starting with `text/html`.
- [ ] The non-API 404 body still contains the literal `404` (existing regression guard, `test/test_public_routes.py:127`).
- [ ] Full pilot suite is green: `90 passed`, `0 failed` (baseline: `1 failed, 89 passed` of `90 collected`).
- [ ] Diff against the base commit touches only `api/four_o_four.py` and/or `app.py`; the locked test file's SHA-256 is unchanged.

### Out of scope

- Any handler other than 404, and any status code other than 404 (405, 500, 401 paths are untouched).
- Response-schema changes to existing endpoints, including the in-view 404 at `api/api_endpoints.py:35` (`{"error": "Account not found"}`), which must keep its exact body.
- A JSON error *schema* contract (field set, error codes, machine-readable types). Only the presence of an `error` key is in scope.
- Logging, metrics, telemetry, auth, session behavior.
- HTML 404 redesign or adding a `404.html` template (no such template exists; `templates/` has no 404 page). Adding one is neither required nor forbidden, but it is not an objective.
- Content negotiation driven by anything the acceptance criteria do not observe (see OQ-4).
- Dependency changes, including installing `ruff`/`black` (see OQ-3). No new packages.
- Editing any test file. `test/test_api_routes.py` is hash-locked; the other test files are regression guards and equally not writable in this chunk.

---

## 3. Current state, root cause, opportunity (PRD §5.2)

### Current state (observed at `01292042`, with citations)

1. `api/four_o_four.py` is two lines: `handle_404()` returns the tuple
   `("404 Not Found", 404)`. A bare `str` body makes Flask serve its default
   `Content-Type: text/html; charset=utf-8`.
2. `app.py:193-195` registers exactly one error handler:
   `@app.errorhandler(404)` → `def page_not_found(e)` → `return handle_404()`.
   The Flask-supplied error argument is accepted by the view and dropped; the
   helper takes no parameters. Import at `app.py:30`.
3. The app serves a JSON API under `/api/*`. Rules present in `app.url_map`:
   `/api/home-content`, `/api/accounts`, `/api/transactions`,
   `/api/account/<int:account_id>`, `/api/transfer`.
4. `api/api_endpoints.py` establishes the app's own in-view JSON error
   convention — `jsonify({"error": ...}), <code>` at lines 8, 19, 30 (401)
   and line 35 (404). A JSON error body keyed `error` is therefore an
   existing in-repo convention, not a new invention (§18 "compose first").
5. Observed today, in-process via `app.test_client()`:
   `GET /api/definitely-not-a-real-endpoint` → `404`,
   `content_type == 'text/html; charset=utf-8'`, body `b'404 Not Found'`.
6. Observed today: `GET /definitely-not-a-real-page` → `404`,
   `'text/html; charset=utf-8'`, body `b'404 Not Found'`. Already correct and
   already asserted green.
7. `app.py:84-93` installs `@app.after_request _record_request_metrics`. It
   runs on 404 responses too and reads `request.url_rule` defensively
   (`"unknown"` when absent). Whatever the 404 handler returns must remain
   something Flask coerces into a normal response object, or this hook raises
   on every 404.

### Root cause

The 404 path has one representation for two audiences. The handler is
registered once, app-wide, and its body and `Content-Type` are fixed at
author time rather than derived per request; nothing in the handler consults
anything about the request. So an API client and a browser receive
byte-identical responses. The defect is the **absence** of a branch, not a
wrong branch.

### Affected public behaviors

| Behavior | Today | After (intended) |
|---|---|---|
| Unmatched path under `/api/` | 404, `text/html`, body `404 Not Found` | 404, `application/json`, body parses as JSON with an `error` key |
| Unmatched non-API path | 404, `text/html`, body contains `404` | unchanged |
| `/api/account/<int:...>` with a non-integer segment (e.g. `/api/account/abc`) | 404 via URL-converter miss → HTML | 404 → JSON; same class as row 1, intended |
| Unmatched `/static/...` path | 404, `text/html` | unchanged (non-API) |
| Bare `/api`, `/apiary`, `/apifoo`, `/API/...` | 404, `text/html` | **unchanged — non-API for this slice** (C6) |
| In-view 404 at `api/api_endpoints.py:35` | 404, JSON, `{"error": "Account not found"}` | **unchanged**; never reaches the error handler |
| 200/400/401/403 API responses | JSON | unchanged |
| Prometheus `after_request` accounting on 404s | recorded with rule `unknown` | unchanged |

### Dependencies and likely files

- Flask 3.1.3 error-handling and response-coercion behavior. No new dependency is expected; if the executor believes one is required, that is a `SPEC_OR_TEST_BLOCKED` report, not a silent install.
- Likely files: `api/four_o_four.py` (handler body) and `app.py` (registration / call site). Both are the chunk's allowed files; nothing else is writable.

### Hard constraints the executor must satisfy

These constrain **observable behavior and existing seams**, not the mechanism.
How the branch is detected and rendered is the executor's decision (PRD §5.5).

- **C1.** On a 404 no route matched, so no resolved Flask endpoint or `url_rule` identifies the request. Any mechanism that depends on a matched rule cannot work here; the discriminator must be derivable from the request as received.
- **C2.** The non-API 404 body must still contain the literal `404`: `test/test_public_routes.py:123-127` (`test_unknown_path_returns_404_page`) asserts `b"404" in response.data` for `/yodawg20044`. That file is not in the chunk's locked set and must not be edited; it is a regression guard.
- **C3.** The handler is invoked by `page_not_found(e)` at `app.py:193-195`. If the helper's arity changes, the call site must change with it, or the error handler raises and Flask returns 500 instead of 404.
- **C4.** The return value must stay compatible with the `after_request` metrics hook (current-state item 7).
- **C5.** `test/test_api_routes.py` is hash-locked. Any needed change there is `TEST_REFACTOR_REQUESTED` (PRD §5.6), never an executor edit.
- **C6.** **Classification boundary (promoted from an open question in review round 1, finding `F-b19c55`).** For this slice, a request is "API" **iff its path begins with `/api/`**. Bare `/api`, `/apiary`, `/apifoo`, and case variants such as `/API/x` are **non-API** and must keep the HTML 404. Verified string behavior that makes this matter: `'/apiary'.startswith('/api')` is `True` while `'/apiary'.startswith('/api/')` is `False`. No locked test observes these paths, so this is a binding constraint rather than a test-enforced one; the validator must report the actual classification for `/api`, `/api/x`, `/apiary`, `/apifoo`, `/API/x` (see the result block). This states *which requests get which representation*; it does not prescribe how the branch is implemented.

### Assumptions

- **A1.** Baseline is known and reproducible at `01292042`: `90 tests collected`; `1 failed, 89 passed`; the single failure is the locked RED test. Re-verified during this planning pass (PRD §5.1 — pre-existing failures are never attributed to the change; here there are none besides RED).
- **A2.** The suite runs offline. Split.io emits loud stdout/stderr noise on every client fixture (`SPLIT_API_KEY not found`, `you passed a null sdk_key`, `✗ Failed to initialize Split.io`, `You already have N factories`). Pre-existing noise on a green baseline, not failures. Judge on pytest's summary line and exit code (OPERATING-RULES §7).
- **A3.** `ruff` and `black` are configured in `pyproject.toml` (`[tool.black]:1`, `[tool.ruff]:17`, `[tool.ruff.lint] select = ["E","F"]`) but installed in **neither** the pilot venv nor on PATH: `No module named ruff`, `No module named black`, `which ruff black` → nothing. The chunk therefore declares a byte-compile build gate instead of asserting a lint gate it cannot run. See OQ-3 and R8.
- **A4.** `pytest.ini` sets `testpaths = test`, `pythonpath = .`, so all commands run with the pilot repo root as cwd.
- **A5.** Tests drive the app in-process through `app.test_client()` (`test/conftest.py`) against a temp SQLite DB created per run. No live server, no network. A default test-client request sends `Accept: */*`, which is why AC-4 must hold without any client-supplied negotiation header.
- **A6.** The chunk-local rollback (`git checkout HEAD -- …`) assumes the executor leaves its edits **uncommitted**. If a commit lands during the chunk, rollback is the sprint-level `git reset --hard 01292042` instead (see §9 and finding `F-a3c91b`).

---

## 4. Risk assessment

| ID | Risk | Severity | Probability | Impact | Mitigation | Human-review trigger |
|---|---|---|---|---|---|---|
| R1 | Non-API 404 regresses — JSON leaks onto HTML paths, or the body loses the literal `404` | High | Medium | Browser 404s break | Both guards run in the focused and full commands; AC-4 asserts `text/html`, AC-5' asserts the `404` substring | Second consecutive failure on the same guard |
| R2 | Boundary over-matching: `/apiary`, `/apifoo`, or bare `/api` classified as API | Medium | Medium | Non-API paths silently become JSON; **no locked test observes it** | C6 makes it a binding constraint, not an open question; the validator must quote the classification of five named paths in its result block | Validator reports any of the five classified against C6 |
| R3 | Handler signature drift breaks the `app.py:193-195` call site | High | Low | Error handler raises → 500 instead of 404 on every 404 | C3; the full suite covers both 404 classes | Any 500 observed on a 404 path |
| R4 | In-view 404 semantics changed (`{"error": "Account not found"}` rewritten or double-encoded) | High | Low | Contract break on an out-of-scope route | Locked `test_api_account_detail_unknown_returns_json_error` asserts the exact message; `api/api_endpoints.py` is not writable | That test fails, or the diff touches `api/api_endpoints.py` |
| R5 | Return shape breaks the `after_request` metrics hook | Medium | Low | Every 404 raises inside the hook | C4; full suite exercises 404s on both branches | Traceback originating in `_record_request_metrics` |
| R6 | Scope creep — other status codes, new templates, logging, error-schema refactor | Medium | Medium | Unreviewed blast radius; §5.5 chunk-adherence violation | Allowed-files list is two files; the scope check diffs against the **base commit**, not `HEAD`, and also reads `git status --porcelain` | Any path outside the allowlist in the diff, or a new file |
| R7 | Executor edits the locked test to make it pass | High | Low | Invalidates the whole evidence chain | Hash lock + write hook (PRD §5.6); AC-6 re-asserts the locked SHA-256 | Any locked-test hash mismatch — hard stop |
| R8 | Lint gate cannot run (A3) and is silently skipped, producing a silent-green shape | Low | Medium | Weaker gate than the chunk claims | The chunk declares the substitution explicitly and records the missing tooling as friction, rather than printing a gate that did not run | Reviewer rejects the substitution (OQ-3) |
| R9 | Scope gate self-defeats if work is committed mid-chunk | Medium | Low | `git diff --name-only HEAD` would go empty and AC-6 would silent-green | Scope check pinned to `01292042` (both `git diff --name-only 01292042` and `01292042..HEAD`) plus `git status --porcelain` | Base-pinned diff and `HEAD` diff disagree |
| R10 | `chunks.json` and this document diverge, so runner-enforced criteria are weaker than the plan's | Medium | Medium | An executor trusting only `chunks.json` could ship a non-API 404 that is `text/html` but no longer contains `404` | §7 marks exactly which criteria are runner-enforced and which are plan-level; the non-runner-enforced ones are still commands in the chunk table and lines in the result block | Reviewer prefers amending `chunks.json` instead (OQ-8) |
| R11 | Test-order or DB pollution makes the run look flaky (API transfer tests mutate balances) | Low | Low | Confusing red unrelated to the change | Full suite is run whole, never sharded; baseline captured for comparison | A failure that does not reproduce on a clean re-run |
| R12 | Trailing-slash and non-GET 404s behave inconsistently with the GET case | Low | Medium | Partial fix, unobserved by locked tests | Named in OQ-1 as an unobserved boundary; C6 fixes only the path-prefix question | Reviewer escalates it to in-scope |

Rollback and recovery for every row: restoring `api/four_o_four.py` and
`app.py` returns the pre-chunk state in seconds. No migration, generated
artifact, config, or persisted state is involved, so recovery is total and
needs no sequencing. Full detail in §9.

---

## 5. Acceptance criteria (observable)

A fresh reviewer with only this document, a shell, and the pilot repo can
decide each row. All commands run from
`/Users/factory/work/quantum-404-lab/quantum-bank` with
`PY=/Users/factory/work/quantum-404-lab/quantum-bank/.venv/bin/python`.

| ID | Observable outcome | How to check | Green means |
|---|---|---|---|
| **AC-1** | An unmatched `/api/*` path returns HTTP 404 | `$PY -m pytest "test/test_api_routes.py::test_api_404_returns_json_error" -q` | the `status_code == 404` assertion passes (`test_api_routes.py:343`) |
| **AC-2** | That response's `Content-Type` starts with `application/json` | same test, assertion at `test_api_routes.py:344` | no `AssertionError: expected application/json 404 body for /api/*` |
| **AC-3** | That response body parses as JSON and has an `error` key | same test, `test_api_routes.py:347-349` | `get_json()` is not `None` and `"error" in body` |
| **AC-4** | An unmatched non-API path returns 404 with `Content-Type` starting with `text/html` | `$PY -m pytest "test/test_api_routes.py::test_non_api_404_preserves_html" -q` | `1 passed` |
| **AC-5** | The non-API 404 body still contains the literal `404` | `$PY -m pytest "test/test_public_routes.py::test_unknown_path_returns_404_page" -q` | `1 passed` |
| **AC-6** | The full existing suite still passes | `$PY -m pytest -q` | `90 passed`, no `failed`, no `error` (baseline `1 failed, 89 passed`) |
| **AC-7** | The change stayed inside the sanctioned surface | `git diff --name-only 01292042`; `git diff --name-only 01292042..HEAD`; `git status --porcelain`; `shasum -a 256 test/test_api_routes.py` | union of changed paths ⊆ {`api/four_o_four.py`, `app.py`}; porcelain shows nothing beyond those two files and the pre-existing `?? .venv/`; hash is exactly `2cf0003eba6b7e7701df74305fc291405961b3bffadcd5290a7c299d26abb2ea` |
| **AC-8** | The touched modules still import and byte-compile | `$PY -m compileall -q api/four_o_four.py app.py` | exit `0`, no output |
| **AC-9** | The C6 boundary holds for paths no test observes | Validator inspects the branch condition in the read-only tree and reports the classification of `/api`, `/api/x`, `/apiary`, `/apifoo`, `/API/x` | `/api/x` → JSON; the other four → HTML |

AC-1 … AC-6 are the pilot spec's five criteria in observable form (its
criterion 4 is split into AC-4 and AC-5 because two different tests assert
the two halves). AC-7 and AC-8 are process gates — chunk adherence and
buildability. AC-9 is the R2 anti-silent-green check and is a **reviewed
report**, not a test.

**Explicitly not an acceptance criterion:** the exact JSON error *message*;
the presence of any key besides `error`; the HTTP reason phrase; the HTML
404's exact body bytes beyond containing `404` (though the executor must
report whether they changed); trailing-slash and non-GET behavior (OQ-1);
and negotiation driven by request headers (OQ-4).

---

## 6. Test strategy (PRD §5.4)

### Boundaries

| Layer | Applies? | What it covers here |
|---|---|---|
| **Unit** | Deliberately not used | A unit test on `handle_404()`'s internals would couple to the implementation the executor is free to choose, and would re-assert the branch predicate in a way that mirrors code. PRD §5.5 warns against exactly that. Rejected on purpose, and the reason is recorded so its absence is not read as an oversight. |
| **Integration** | Yes (primary) | Flask `test_client()` requests through the real WSGI stack, real error-handler registration, real `after_request` hooks. "The `Content-Type` of a 404" is only a meaningful claim at this level. |
| **Contract** | Yes | The `/api/*` error envelope is client-facing: status 404 + `application/json` + a parseable body containing `error`. Asserted through the public HTTP surface only. |
| **E2E** | No | The pilot has no browser/E2E harness; adding one is out of scope. |

### Locked test candidates (already authored, pre-existing)

Locked file: `test/test_api_routes.py`
SHA-256: `2cf0003eba6b7e7701df74305fc291405961b3bffadcd5290a7c299d26abb2ea`
(verified by `shasum -a 256`, and identical to the manifest at
`framework/tools/phase-1-locks/test/test_api_routes.py.lock.json`, whose
`accepted_assertion` is `application/json`, `accepted_at`
`2026-08-16T03:57:31Z`).

Authored at commit `01292042` (that file only), so **no `test_designer`
round fires for this chunk** and the plan's author did not write the tests
that will judge the plan (OPERATING-RULES §22).

| Test id | Role | Baseline |
|---|---|---|
| `test/test_api_routes.py::test_api_404_returns_json_error` (`:340-349`) | RED behavior under test (AC-1..AC-3) | **fails** |
| `test/test_api_routes.py::test_non_api_404_preserves_html` (`:353-357`) | Anti-regression on the HTML branch (AC-4) | passes |
| `test/test_api_routes.py::test_api_account_detail_unknown_returns_json_error` (`:62-70`) | Guards the in-view 404 contract, exact message (R4) | passes |

### Additional regression guards (not locked by the chunk, equally not editable)

| Test id | Guards |
|---|---|
| `test/test_public_routes.py::test_unknown_path_returns_404_page` (`:123-127`) | Non-API 404 body still contains `404` (C2, R1, AC-5) |
| `test/test_api_routes.py`, remaining 18 tests | 200/400/401/403 JSON contracts unchanged |
| `test/test_banking_routes.py`, `test/test_demo_rollout.py`, `test/test_a_models_bootstrap.py`, `test/test_z_split_shutdown.py` | Whole-app regression (AC-6) |

### Valid-RED record (PRD §5.4), captured pre-implementation

```json
{
  "behavior": "an unmatched /api/* path returns a 404 whose Content-Type is application/json and whose body parses as JSON containing an 'error' key",
  "test_id": "test/test_api_routes.py::test_api_404_returns_json_error",
  "test_sha256": "2cf0003eba6b7e7701df74305fc291405961b3bffadcd5290a7c299d26abb2ea",
  "command": "/Users/factory/work/quantum-404-lab/quantum-bank/.venv/bin/python -m pytest test/test_api_routes.py::test_api_404_returns_json_error -q",
  "expected_failure": "assertion on response.content_type mismatches: 'application/json' required, HTML served",
  "exit_code": 1,
  "observed_failure": "AssertionError: expected application/json 404 body for /api/*, got 'text/html; charset=utf-8' at test/test_api_routes.py:344",
  "classification": "behavioral-red"
}
```

This is a valid RED: the test collected, executed, reached its intended
assertion at `test_api_routes.py:344`, and failed because the required
behavior is absent. Not an import error, not a missing fixture, not an empty
selection, not an unrelated assertion. The sibling
`test_non_api_404_preserves_html` passes at baseline, which is correct — it
asserts *preserved* behavior, so it must be green before and after, and it is
a regression guard rather than part of the RED.

### Test-quality standards for the validator (PRD §5.7)

Reject private/internal coupling, weak truthiness, tautologies, conditional
assertions, timing sleeps, mocks of the subject under test, and assertions
that replay implementation details. The locked assertions touch only the
public surface (`status_code`, `content_type`, `get_json()`), which is the
line to hold.

---

## 7. Chunk plan

One chunk; sequential by definition, so no parallelism question arises
(PRD §5.5).

**Consistency with `sprint/chunks.json` (finding `F-7e2d04`, disposition (b)).**
`chunks.json` `c1` is the **runner-enforced minimum**: its five
`observable_criteria` and its two `commands` are what the loop mechanically
gates on. This section is a **superset**, not a byte-for-byte mirror. The
extra material — the `404`-substring guard on the non-API body, the compile
gate, the base-pinned scope check, the C6 classification report — is marked
below as *plan-level (not runner-enforced)* and is carried into the result
block so it is reported mechanically rather than trusted to prose. No claim
is made here that the two files are identical. If the reviewer prefers the
stronger option — amending `chunks.json` itself — that is OQ-8, and the
amendment must land in the same round as this document's re-hash.

### CHUNK `c1`: content-negotiated 404

**Type:** code change (behavior) · **Depends on:** nothing · **Parallelizable:** no · **Risk level:** Medium · **Est. duration:** 15-30 min

**Bounded outcome (scope, verbatim from `chunks.json`):**
> Make 404 responses content-negotiated: requests under `/api/*` must receive
> a parseable JSON error body with `Content-Type: application/json`, while
> non-API paths keep the existing HTML 404. Only the 404 handling changes;
> all other routes and status codes are unaffected.

**Observable success criteria**

| # | Criterion | Enforcement |
|---|---|---|
| 1 | `GET` an unmatched `/api/*` path returns HTTP 404 | runner-enforced (`chunks.json`) |
| 2 | That 404 response's `Content-Type` starts with `application/json` | runner-enforced |
| 3 | That 404 response body parses as JSON and contains an `error` key | runner-enforced |
| 4 | `GET` an unmatched non-API path still returns HTTP 404 with `Content-Type` `text/html` | runner-enforced |
| 5 | The full existing test suite still passes (`90 passed`) | runner-enforced |
| 6 | The non-API 404 body still contains the literal `404` | plan-level (AC-5); command in the table below, line in the result block |
| 7 | Touched modules byte-compile | plan-level (AC-8) |
| 8 | Diff against `01292042` ⊆ the allowed files; locked-test hash unchanged | plan-level (AC-7) |
| 9 | C6 classification holds for `/api`, `/apiary`, `/apifoo`, `/API/x` | plan-level (AC-9), validator report |

**Dependencies and semantic interfaces** (not merely file paths)
- Flask error-handler registration: `app.errorhandler(404)` → `page_not_found(e)` (`app.py:193-195`) → `handle_404()` (`api/four_o_four.py`). This seam between the two allowed files is the only interface being reshaped; if the helper's arity changes, the call site changes with it (C3).
- The `after_request` metrics hook (`app.py:84-93`) consumes whatever the handler returns (C4).
- The in-view JSON error convention in `api/api_endpoints.py` is a **read-only reference** for what an error body looks like in this codebase; that file is not writable here.
- No shared schema, configuration, generated artifact, migration order, or API contract is shared with any other chunk (there is no other chunk).

**Files**
- Allowed implementation files (writable): `api/four_o_four.py`, `app.py`
- Locked test file (read-only, hash-enforced): `test/test_api_routes.py` @ `2cf0003eba6b7e7701df74305fc291405961b3bffadcd5290a7c299d26abb2ea`
- Read-only context worth reading first: `api/api_endpoints.py`, `test/test_public_routes.py`, `test/conftest.py`, `pytest.ini`
- Any other path: out of bounds. Needing one is `SPEC_OR_TEST_BLOCKED`, not a quiet edit.

**Commands** (cwd `/Users/factory/work/quantum-404-lab/quantum-bank`;
`PY=/Users/factory/work/quantum-404-lab/quantum-bank/.venv/bin/python`)

| Beat | Command | Expected output / pass condition |
|---|---|---|
| RED (pre-impl, must fail) | `$PY -m pytest test/test_api_routes.py::test_api_404_returns_json_error -q` | exit `1`; `AssertionError: expected application/json 404 body for /api/*, got 'text/html; charset=utf-8'` at `test_api_routes.py:344` |
| Focused GREEN *(runner-enforced)* | `$PY -m pytest test/test_api_routes.py -v` | exit `0`; `21 passed` (baseline for this file: `1 failed, 20 passed`); both `test_api_404_returns_json_error` and `test_non_api_404_preserves_html` PASSED |
| Full suite *(runner-enforced)* | `$PY -m pytest -q` | exit `0`; `90 passed`; no `failed`, no `error` (baseline `1 failed, 89 passed`) |
| Non-API body guard *(plan-level)* | `$PY -m pytest test/test_public_routes.py::test_unknown_path_returns_404_page -q` | exit `0`; `1 passed` |
| Build / compile gate *(plan-level)* | `$PY -m compileall -q api/four_o_four.py app.py` | exit `0`, no output |
| Lint gate | **substituted by the compile gate.** `ruff` and `black` are configured in `pyproject.toml` but installed in neither the venv nor PATH (A3, R8, OQ-3). Do **not** install them inside this chunk — that is an out-of-scope dependency change. | n/a; report the substitution, never a gate that did not run |
| Scope check *(plan-level)* | `git diff --name-only 01292042` · `git diff --name-only 01292042..HEAD` · `git status --porcelain` · `shasum -a 256 test/test_api_routes.py` | union of changed paths ⊆ {`api/four_o_four.py`, `app.py`}; porcelain adds nothing beyond those files and the pre-existing `?? .venv/`; locked hash unchanged |

The two rows marked *(runner-enforced)* are exactly
`chunks.json.commands`. The rest are additional verification the executor
runs and reports (OPERATING-RULES §18.3: every chunk boundary has a
script-runnable check).

**Noise to expect and ignore:** Split.io output on stdout/stderr —
`⚠ WARNING: SPLIT_API_KEY not found`, `factory_instantiation: you passed a
null sdk_key`, `✗ Failed to initialize Split.io`, `You already have N
factories`. Pre-existing on a green baseline (A2). Judge on pytest's summary
line and exit code, never on the absence of log noise (OPERATING-RULES §7).

**Human-review trigger (any one → pause; do not retry blindly)**
- Locked-test hash changed, or any write to `test/**` was attempted.
- A path outside the allowed list appears in the base-pinned diff or in `git status --porcelain`, or a new file is added.
- Any 404 path returns 500, or a traceback originates in `_record_request_metrics`.
- `test_api_account_detail_unknown_returns_json_error` fails (in-view 404 contract disturbed, R4).
- The validator reports a C6 violation (AC-9) even though the suite is green.
- Both auto-retries exhausted with the chunk still red.

**Rollback method**
`git checkout HEAD -- api/four_o_four.py app.py` — valid while the
executor's edits are uncommitted (A6). If a commit landed during the chunk,
use the sprint-level `git reset --hard 01292042` instead. Recovery time:
seconds. Nothing else to undo — no migration, config, generated artifact, or
persisted state. Verification of the rollback: `$PY -m pytest -q` must
reproduce the baseline exactly (`1 failed, 89 passed`).

**Retry and escalation behavior** (from `sprint/config.json`)
- `retry_threshold: 1`, `max_auto_retries: 2`, `retry_delay_seconds: 5`, `fail_closed: true`.
- `REJECT_IMPLEMENTATION` → rollback, then a fresh executor attempt carrying the validator's finding but **not** the previous executor transcript; capped at 2.
- `REJECT_TEST` → back to test design; downstream locks invalidated. The executor never edits the locked test; it reports `TEST_REFACTOR_REQUESTED` (PRD §5.6).
- `REPLAN` (scope or architectural invalidation — e.g. the reviewer moves OQ-1 or OQ-4 in-scope) → back to GROK; this document is amended and re-hashed, and reviewer approval must re-bind to the new hash (PRD §5.3).
- Retries exhausted, ambiguous ownership, or any human-review trigger → `HUMAN_DECISION` with the reconcile packet.
- Validators are `grok-4.5` (grok-family) and `kimi-k3` (kimi-family). A validator that returns nothing is not a pass (`fail_closed: true`).

**Standardized result block** (executor must emit this shape verbatim)

```
CHUNK c1 STATUS: SUCCESS | FAILED | SPEC_OR_TEST_BLOCKED | TEST_REFACTOR_REQUESTED

TDD cycle:
  RED verified before implementation:  YES/NO   (exit code + assertion line)
  Focused GREEN after implementation:  YES/NO   (test/test_api_routes.py -v summary)
  Full suite:                          YES/NO   (pytest -q summary line)
  Compile gate:                        YES/NO   (compileall exit code)
  Lint gate:                           SUBSTITUTED (ruff/black absent, A3)

Observable criteria:
  1 /api/* unmatched -> 404:                  PASS/FAIL
  2 Content-Type application/json:            PASS/FAIL
  3 body parses as JSON with 'error' key:     PASS/FAIL
  4 non-API 404 still text/html:              PASS/FAIL
  5 full suite green (90 passed):             PASS/FAIL
  6 non-API 404 body still contains "404":    PASS/FAIL
  non-API body unchanged (bytes):             YES/NO  (<observed bytes>)

C6 classification actually implemented:
  /api/x   -> JSON/HTML
  /api     -> JSON/HTML
  /apiary  -> JSON/HTML
  /apifoo  -> JSON/HTML
  /API/x   -> JSON/HTML

Scope:
  files changed (vs 01292042): <git diff --name-only 01292042>
  files changed (01292042..HEAD): <git diff --name-only 01292042..HEAD>
  working tree:                <git status --porcelain>
  locked test sha256:          <shasum -a 256 test/test_api_routes.py>  (must be unchanged)
  files outside allowlist:     NONE / <list>

Trade-offs and decisions: <what was chosen and what was rejected, briefly>
Issues: NONE / <list>
```

---

## 8. Open questions

### For the reviewer to confirm or correct

| ID | Question | Why it matters | Planner's default if unanswered |
|---|---|---|---|
| **OQ-1** | C6 fixes the path-prefix boundary. Trailing-slash forms (`/api/` exactly) and **non-GET** methods on unmatched `/api/*` paths remain unobserved by any test. In-scope or not? | An under-broad fix would leave `POST /api/nope` serving HTML, which the spec arguably wants as JSON, but no criterion observes it (R12). | Out of scope for this slice; C6 is stated in terms of the path only, so whatever the executor does applies uniformly across methods. Do **not** add tests to the locked file. |
| **OQ-2** | Is `error` the only required key, with message text unconstrained? | If the reviewer wants a message contract, that is a schema decision that belongs in the plan, not in the executor's judgment. | Only `error` is required; the message is the executor's choice and is reported in the result block. |
| **OQ-3** | Is the compile gate an acceptable substitute for the lint/format gate, given `ruff`/`black` are configured in `pyproject.toml` but absent from the venv and PATH? | PRD §5.5 asks for lint and build commands. Claiming a lint gate that cannot run is a silent-green shape (R8, OPERATING-RULES §7); installing the tools inside the chunk is an out-of-scope dependency change. | Substitute the compile gate, record the limitation, and file the missing dev tooling as **friction to fix outside this sprint** — §18.4 asks for inline friction fixes, but this friction lives in the pilot repo's environment, not in a framework primitive the chunk touches. |
| **OQ-4** | The spec frames the discriminator as the request path. Should any request-header negotiation be honored? | AC-4 must hold for a default test-client request, whose `Accept` is `*/*` (A5). Broadening the discriminator without a locked test is unobserved scope (R6). | Out of scope; path-based classification only, exactly as the spec's `/api/*` framing states. |
| **OQ-5** | For the non-API branch, is "contains `404`" the whole requirement, or must the current body `404 Not Found` be byte-preserved? | `test_public_routes.py:127` asserts only the substring, so a body rewrite could pass while changing browser-visible output (R1). | Substring is the contract; the result block's `non-API body unchanged (bytes)` line makes any change visible to the reviewer instead of silent. |
| **OQ-6** | The evidence directory sits outside `framework_root`, which raises the H-9 preflight warning by design for this pilot. Confirm it is expected and not a gate failure. | A reviewer meeting H-9 for the first time could reasonably read it as a preflight defect. | Expected and intended per the run config; not a finding. |
| **OQ-7** | Confirm the baseline disposition: `90 collected`, `1 failed / 89 passed`, the sole failure being the locked RED test, with Split.io noise on a green baseline. | PRD §5.1 requires recording pre-existing failure state and never attributing it to the change. | Baseline as recorded in §3/A1-A2 is the reference; any other failure appearing later belongs to the change. |
| **OQ-8** | Should `sprint/chunks.json` be amended so the runner-enforced criteria include the non-API `404`-substring guard (and its command), or does the plan-level marking in §7 suffice? | `chunks.json` is what the loop mechanically gates on; a superset that lives only in this document depends on the executor and validator reading it (R10). | The §7 marking plus the result-block lines suffice for this slice. Amending `chunks.json` is the stronger option and is available; if the reviewer chooses it, the JSON edit and this document's re-hash must land in the same round. |

### Round-1 findings already dispositioned in this document

Recorded so the reviewer can see what moved rather than re-deriving it.
Source: `sprint/evidence/reconcile-packet.txt`, plan hash
`ffad2409a689058b7f77e3d1088d5c61af4a48d707b4fdb963ce013af16db903`.

| Finding | Severity | Disposition here |
|---|---|---|
| `F-a3c91b` — scope check used `git diff --name-only HEAD`, which silent-greens if work is committed mid-chunk | medium | **Accepted.** AC-7 and the chunk scope check are pinned to `01292042`, add `01292042..HEAD` and `git status --porcelain`, and A6/§9 state that chunk-local rollback assumes uncommitted edits. New risk row R9. |
| `F-7e2d04` — plan claimed a mirror of `chunks.json` while criterion 4 diverged | medium | **Accepted, option (b).** §7 now names `chunks.json` as the runner-enforced minimum and marks each criterion's enforcement; the `404`-substring guard is plan-level (AC-5) with its own command and result-block line. Option (a) is offered as OQ-8. New risk row R10. |
| `F-b19c55` — the `/api/` boundary should bind the executor, not sit as an open question | medium | **Accepted.** Promoted to hard constraint **C6**, with the five named paths classified, plus AC-9 and a validator report line in the result block. |
| `F-e8a012`, `F-a82f3b1` — compile gate substituted for lint | low | **Accepted.** Substitution kept and declared; no tool install inside the chunk; missing dev tooling recorded as out-of-sprint friction (OQ-3). |
| `F-55d0aa`, `F-e51f8a3` — non-API body bytes not strictly enforced | low | **Accepted.** Substring remains the contract; the result block now carries `non-API body unchanged (bytes)` so the report is mechanical rather than prose. |
| `F-c94e7d2` — confirm the `/api/` prefix scoping | low | **Accepted**, subsumed by C6. |

---

## 9. Rollback and recovery (sprint level)

| Level | Method | Precondition | Recovery time | Verification |
|---|---|---|---|---|
| Chunk `c1` | `git checkout HEAD -- api/four_o_four.py app.py` | executor edits are uncommitted (A6) | seconds | `$PY -m pytest -q` reproduces `1 failed, 89 passed` |
| Chunk `c1`, post-commit | `git reset --hard 01292042` on `factory/api-404-json` | a commit landed during the chunk | seconds | `git log --oneline -1` shows `01292042`; suite reproduces baseline |
| Sprint | `git reset --hard 01292042` on `factory/api-404-json`; branch is sprint-local, nothing is pushed, `create_pr: false` | none | seconds | as above |
| Data | none required — no migration, schema change, or persisted state; tests build a temp SQLite DB per run via `test/conftest.py` | n/a | n/a | n/a |

No forward-fix-only path exists in this sprint: every change is a two-file
source edit that `git checkout`/`git reset` fully reverses. Note that
`?? .venv/` is untracked and pre-existing; no rollback step should touch it.

---

PLAN_HASH: <sha256 placeholder — runner computes real value after rendering>
# Phase 3 — Execution brief: read-only `GET /profile` (QuantumBank)

**Status:** EXECUTING on `factory/phase-3-slice` (framework) and
`factory/phase-3-profile` (pilot). The human plan-approval gate is PASSED
(`phase-2/APPROVAL.md`, plan-v1 bound to `sha256:72eccff5…`).

## Objective

Build the approved plan-v1 end-to-end on the pilot: a read-only `GET /profile`
page rendering the session-authenticated user's `username`, `email`,
`full_name`, and a themed **address** for the demo identity Jean-Luc Picard.
Run the full adversarial-sprint execution loop: test-authorship (independent
family) → lock → valid-RED → cheap executor → per-chunk cross-family
validation. One real slice through the whole plan → execute → review cycle.

## Gate status

- **Plan approval:** PASSED (human, 2026-08-07, hash-bound).
- **Final merge:** NOT authorized — human decision after cross-family review.
  Do not self-merge.

## Repos

- **Framework:** `/Users/factory/work/adversarial-sprint-dev`, branch
  `factory/phase-3-slice`, off `main @ cfb1a32`.
- **Pilot:** `/Users/factory/work/quantum-bank--llms-txt-pilot`, branch
  `factory/phase-3-profile`, off `8a10711d` (Phase-1 charset fix committed,
  plan-v1 line anchors verified, 87 tests green, 26 routes).

### Why 8a10711d and not pilot main

Pilot `main` diverged via `pilot/sitemap` + `pilot/ai-discovery` merges and a
stale-test-count fix, shifting the line anchors plan-v1 was read against.
`8a10711d` preserves the exact tree the planner cited: banking block at
`app.py:186`, seed at `models.py:431`, `_sql` at `:52`, `get_user_by_username`
at `:568`. `8a10711d` is not an ancestor of the current pilot `main` (history
was rewritten during cleanup), but it is the correct tree state.

## Model seats (§17.1 — amendment now live on main)

| Role | Model | Family | Pin reason |
|---|---|---|---|
| Orchestrator/driver | Factory (this session) | — | Conducts, no role seat |
| Test-author | `claude-opus-5` | anthropic | ≠ executor family (invariant 1) |
| Executor | ~~`gpt-5.4-mini` (openai)~~ → `glm-5.2` | zhipu | Cheap tier; no family invariant binds (§17.1). Planned openai seat was down (KI-1); substituted glm-5.2 with human approval. Separation preserved: zhipu ≠ anthropic/xai/google |
| Validator 1 | `grok-4.5` | xai | ≠ executor family; pinned (§17.2) |
| Validator 2 | `gemini-3.1-pro-preview` | google | ≠ executor family; pinned (§17.2) |

No collisions: openai executor vs xAI/google validators is clean.

## Test file split (execution decision)

Plan-v1 §6 specifies "New `test/test_profile.py`." The per-chunk lock-and-execute
loop requires that each chunk's tests be independently locked before that
chunk's implementation. A single file locked after chunk 1 would block the
chunk 2 test-author from adding tests (the hook denies edits to locked files
for ALL agents, not just the executor).

**Decision:** split into three files, one per chunk. Test content and intent
are unchanged from the plan; only the file organization differs.

| File | Chunk | Tests |
|---|---|---|
| `test/test_profile_model.py` | 1 | `get_user_profile` unit: key-set contract, None for unknown, address non-empty |
| `test/test_profile_route.py` | 2 | Route+template: auth redirect, no-leak, field presence, no internal columns, stale session (A5), DB-vs-session (A3) |
| `test/test_profile_seed.py` | 3 | Seed identity: fresh-DB Picard fields, login still works, A1 integration |

## Per-chunk execution loop (PRD §5.2–5.5)

For each chunk, in order:

1. **Test-author** (`claude-opus-5`) writes the chunk's test file from plan §6
   + amendments. Executor never touches it.
2. **Lock** the test file by SHA-256 (`phase-1/scripts/lock.py`). Lock manifests
   go to `phase-1/locks/` (the hook's default `LOCKS_DIR`), so the hook
   enforces both Phase-1 and Phase-3 locks.
3. **Valid-RED gate** (`phase-1/scripts/valid-red.py`) — tests must fail for the
   expected behavioral reason, not import/syntax/fixture errors.
4. **Executor** (`gpt-5.4-mini`) implements to GREEN, touching only the chunk's
   allowed implementation files. The `locked-test-guard.py` hook blocks test
   edits.
5. **GREEN verification** (`phase-1/scripts/verify-green.py`) — hash matches +
   test passes.
6. **Cross-family validation** — `grok-4.5` + `gemini-3.1-pro-preview`,
   read-only, fresh context, review spec + diff + test evidence. Reject →
   cheap retry vs small diff, cap 2 rounds, then decision packet.
7. Only an ACCEPTED chunk unblocks the next.

## Chunk specs (from plan-v1, frozen)

### Chunk 1 — profile read model (data layer)
- **Interface:** `get_user_profile(user_id: int) -> dict | None` in `models.py`
- **Returns:** exactly `{"username", "email", "full_name", "address"}` or `None`
- **Named columns, NOT `SELECT *`** (contrast `get_user_by_username:572`)
- **Address:** module-level constant `PROFILE_DEMO_ADDRESS` with env override
  `os.environ.get("PROFILE_DEMO_ADDRESS", default)` (A4), default = Picard string
- **Allowed files:** `models.py` only
- **Test file:** `test/test_profile_model.py`
- **Accepted assertion:** `profile key-set equals contract`

### Chunk 2 — route + template (delivery layer)
- **Interface:** `handle_profile()` in new `api/profile.py`, registered as
  `@app.route("/profile")` in `app.py` banking block
- **Auth guard:** `if "user_id" not in session: return redirect(url_for("login"))`
- **Data from DB:** `get_user_profile(session["user_id"])`, not session copies
- **None → redirect to login** (fail-closed, no 500)
- **Template:** `templates/profile.html`, standalone (no base.html, no extends),
  reusing navbar/banking.css structure of `account_detail.html`
- **Allowed files:** `api/profile.py` (new), `templates/profile.html` (new),
  `app.py` (one route registration + one import)
- **Test file:** `test/test_profile_route.py`
- **Accepted assertion:** `profile requires authenticated session`

### Chunk 3 — demo seed identity
- **Interface:** seed tuple at `models.py:431` →
  `("demo", "jpicard@starfleet.fed", "Jean-Luc Picard")`
- **`username` stays `"demo"`** (login credential)
- **Allowed files:** `models.py` (seed tuple only)
- **Test file:** `test/test_profile_seed.py`
- **Accepted assertion:** `seeded identity is Jean-Luc Picard`

## Amendments A1–A5 (binding acceptance criteria)

- **A1:** After `POST /login {username: demo}` on fresh DB, `GET /profile` body
  contains `Jean-Luc Picard`, `jpicard@starfleet.fed`, `USS Enterprise NCC-1701-D`.
- **A2:** Risk table carries PRD §5.2 columns (doc-level, already in plan).
- **A3:** DB-vs-session source-of-truth test: diverge session from DB, assert
  page follows DB via `get_user_profile`, not session copy.
- **A4:** Address constant: default = Picard string; env override
  `PROFILE_DEMO_ADDRESS`.
- **A5:** Stale-session test: `with client.session_transaction() as s:
  s['user_id'] = <nonexistent id>`, expects redirect to login.

## Operating rules

- **Zero-buffer budget:** `droid exec` calls run sequentially; observe-then-proceed.
- **Envelopes:** `--output-format json` → `phase-3/build-evidence/`.
- **Telemetry rows:** gitignored `telemetry/runs.jsonl` (shape: `telemetry/SCHEMA.md`).
- **Commit-body recipe:** `Model:`, `Role:`, `Telemetry-row:`, `Findings:` trailers.
- **Validators:** `--auto high`, `--enabled-tools Read,Glob,Grep,LS,Execute`.
  KI-2 risk: `Execute` is a write vector at `high`. Mitigation: check `git status`
  after each validator run for stray writes.
- **Never self-approve** any gate. Never self-merge.
- **No Phase-5 exec-cadence wrapper.**

## Exit criteria (PRD §11 Phase 3)

- `/profile` built; tests independently authored, locked, valid-RED then GREEN.
- Each chunk ACCEPTED by cross-family validation.
- Slice landing ACCEPT / ACCEPT-WITH-NITS.
- Telemetry rows for every `droid exec` invocation.
- `droid-wiki/overview/` Phase-3 entry (template: `phase-2-planning-slice.md`).
- Decision packet only if a chunk hits non-convergence.
- Replayable demo + baseline comparison arm.
- **Human merge gate** — present the slice, do not merge.

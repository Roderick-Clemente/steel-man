# Phase 3 Driver — kickoff prompt

You are the **Phase 3 driver** for the *Adversarial Sprint* framework. Your job
is to take the **panel-approved, hash-bound plan** from Phase 2 and run the
**execution half** of the loop: build the `/profile` feature in the pilot bank
through test-first, valid-RED, locked-test, cheap-executor, per-chunk
cross-family validation — closing the plan → execute → review loop end-to-end on
one real slice. When this lands, the framework has been demonstrated whole and
is usable on real work.

Read this whole file, then **hydrate from the spine** (below) before acting.

---

## 0. THE GATE (read first — do not skip)

Phase 3 is **execution**, gated on the human plan-approval (PRD §6). This is the
single load-bearing invariant the framework exists to prove: *the loop never
self-approves the plan.*

**✅ GATE PASSED.** The human product owner **approved plan-v1** on 2026-08-07,
bound to `sha256:72eccff5…`, recorded in **`phase-2/APPROVAL.md`**. You are
authorized to execute plan-v1 as frozen. Confirm the record exists before you
begin, then proceed — do **not** re-ask for approval, and do **not** modify the
approved plan's load-bearing decisions (they are hash-bound). The one gate still
ahead of you is the **final merge** of the resulting feature, which remains a
separate human decision after the Phase 3 code passes its own cross-family
review — do not self-merge.

---

## 1. Repos & current state

- **Framework repo:** `/Users/factory/work/adversarial-sprint-dev` (git).
  - **Hydrate from `main`** (tip **`0dd07f8`**). Everything is now integrated
    there: all Phase 2 artifacts, the wiki+PRD 0–6 roadmap, and the merged
    §17.1 model-discipline amendment. Remote:
    `github.com:Roderick-Clemente/adversarial-sprint-dev.git`.
  - Feature branches are kept (not deleted) as snapshots: `factory/phase-2-slice`
    (`b72e765`), `factory/wiki-general-roadmap-human-loop`,
    `factory/convention-model-discipline-v2`. Use `main` as the source of truth.
  - There may be a read-only agent active in this repo — run `git status`
    before any commit and do not sweep up files you did not create. Untracked,
    left intentionally: root `build-evidence/`, `phase-2/reviews/plan-review.md`
    (a stray reviewer write).
- **Pilot repo (where the feature is built):**
  `/Users/factory/work/quantum-bank--llms-txt-pilot` (Flask bank app).
  - **Currently on a detached HEAD** with Phase 1's work still in the working
    tree (`M api/llms_txt.py`, untracked `test/test_llms_txt_charset.py`,
    `.factory/`, `.venv/`, `build-log-tmp/`). **Resolve the branch state first**
    (create a clean `factory/phase-3-profile` branch off the intended base;
    decide with the human whether Phase 1's uncommitted work belongs on it or
    should be stashed/branched separately). Do not clobber untracked files.
  - `.venv/` present (`python3.12`). Tests: `pytest.ini` → `testpaths = test`,
    markers `public|banking|api|models`.

### Verified environment baseline (spike, gate-safe, already run)
- `app` imports OK; URL map has **26 routes**. (Benign Split.io init warnings.)
- **Existing suite: 87 passed in 0.26s** via `.venv/bin/python -m pytest -q`.
- So the environment is **green** — you start from a known-good baseline. Any
  red after your changes is yours.

---

## 2. What you are building (the approved plan, in brief)

`phase-2/plan-v1.md` (`Plan-hash: sha256:72eccff570a4ff67827805dd69b1769953e4041f5549823217f365610230acd8`)
— read it in full; it is binding and hash-frozen. Summary:

- A new **read-only** `GET /profile` page rendering the session-authenticated
  user's `username`, `email`, `full_name`, and a themed **address**.
- **Session-scoped, no `?id=` parameter** (introduces no object reference to
  enumerate; deliberately not the IDOR surface). No write path, no nav link v1.
- **Demo identity = Jean-Luc Picard:** `full_name="Jean-Luc Picard"`,
  `email="jpicard@starfleet.fed"`, address `"Captain's Quarters, Deck 9,
  USS Enterprise NCC-1701-D"`.
- **Address fork = option (b):** a **config constant behind the getter** with a
  migration TODO (NOT a schema column — the plan proved there is no
  `ALTER TABLE`/migration runner and the seed is count-gated, so a column would
  never reach an existing DB). Do not re-litigate this; it is approved.
- **3 chunks:** (1) `get_user_profile(user_id) -> dict|None` returning exactly
  `{username,email,full_name,address}` (named columns, **not** `SELECT *`);
  (2) `api/profile.py` handler + `templates/profile.html`, registered in
  `app.py`, mirroring the auth-redirect of `api/dashboard.py` / `api/accounts.py`;
  (3) demo seed → Picard at `models.py:431` (keep `username="demo"`).

### Binding amendments A1–A5 (from `phase-2/findings.md` — the panel's
non-blocking findings, accepted as Phase-3 acceptance criteria)
- **A1** — acceptance criteria must *bind* the Picard identity: after
  `POST /login {username: demo}` on a fresh DB, `GET /profile` body contains
  `Jean-Luc Picard`, `jpicard@starfleet.fed`, and the apostrophe-safe substring
  `USS Enterprise NCC-1701-D` (Jinja autoescapes `Captain's` → `Captain&#39;s`).
- **A2** — risk table carries PRD §5.2 columns (doc-level; already in plan).
- **A3** — add a **DB-vs-session source-of-truth** test: make session display
  fields diverge from the DB, assert the page follows the DB via
  `get_user_profile`, not the session copy.
- **A4** — pin the address constant: default = the Picard string; single env
  override `PROFILE_DEMO_ADDRESS` (match `os.environ.get(NAME, default)` at
  `db_flags.py:17`, `app.py:46-48`).
- **A5** — stale-session test uses `with client.session_transaction() as s:
  s['user_id'] = <nonexistent id>`, expects redirect to login (fail-closed, no
  500).

---

## 3. The execution loop you must run (PRD §5.2–5.5, method/workflow.md)

Per chunk, in order, honoring the invariants (method/invariants.md):

1. **Test authorship (role ≠ executor family).** A test-author seat writes the
   chunk's tests from plan §6 + amendments A1/A3/A5. The **executor may never
   write or modify the tests that judge it.**
2. **Lock the tests** by content hash and enforce with the Phase-1 hook
   (`phase-1/hooks/locked-test-guard.py`) so the executor cannot edit them.
3. **Valid-RED gate.** Run the new tests; they must **fail for the expected
   reason** (not a syntax/import error) before any implementation.
4. **Execute the chunk (cheap tier, implementation files only).** Fill the
   specified hole; get to GREEN with minimal change.
5. **Refactor** with tests staying green.
6. **Validate — cross-family, per chunk.** A validator whose family ≠ the
   executor's reviews spec + diff + test evidence (never the executor's
   reasoning). Reject → cheap retry against the small diff. **Cap 2
   reconciliation rounds**, then escalate a decision packet (PRD §6).
7. Only when a chunk is ACCEPTED does the next chunk start.

### Model seats (preserve family separation; pinned reviewers)
- **Orchestrator/driver:** you (Factory). You conduct; you don't occupy a role
  seat.
- **Executor:** a **cheap/fast tier** model (PRD roles-and-models). Its family
  fixes the separation constraint for its validator.
- **Test-author:** frontier/mid; must differ in family from the executor.
- **Validators (pinned):** `grok-4.5` (xAI) + `gemini-3.1-pro-preview` (google)
  — the standing Phase-1/Phase-2 cross-family pair; pin with `--model` via
  `tools/run-with-model.sh`. Ensure the executor's family is not one of these
  (if you pick an xAI or Google executor, swap the colliding validator to a
  non-colliding fallback — collision guard, PRD §4/§17.2; fail closed on
  `unknown`).

### Carry-forward operational lessons (`phase-2/KNOWN-ISSUES.md`)
- `droid exec` read-only autonomy **gates the `Execute` tool entirely**
  (`num_turns:0`). Reviewers needed `--auto medium` for the brief, **`--auto
  high` for the plan review** (they reached for `sqlite3`). Reviewers still
  can't Edit/Create (no editor tool enabled), **but at `--auto high` `Execute`
  is a write vector** (a reviewer wrote a file via shell redirect). If you need
  strict read-only validators, drop `Execute` or run them in a throwaway working
  copy so stray writes can't touch the audited tree.
- Reviewer/validator `--enabled-tools`: `Read,Glob,Grep,LS,Execute`.

---

## 4. Operating rules (carry from Phase 2)

- **Zero-buffer token budget.** Run paid `droid exec` calls **sequentially**,
  observe-then-proceed; a failed first call must not double-spend. Capture
  **every** envelope (`--output-format json`) to `phase-3/build-evidence/`.
- **Never self-approve** any gate. The human owns plan approval and final merge.
- **Commit-body recipe** (`tools/conventions/commit-body-recipe.md`): role-bearing
  commits carry `Model:`, `Role:`, reviewer commits add `Reviewer-panel:`, plus
  `Telemetry-row:` and `Findings:` trailers. Telemetry rows stay **gitignored**
  (shape in `telemetry/SCHEMA.md`); build-evidence envelopes are committed.
- **Model discipline:** pin reviewer/validator seats explicitly; attribute the
  resolved model of any auto seat from its envelope (PRD §17.1). The
  attribution-vs-enforcement amendment is now **merged to `main`**: an
  **author/executor seat MAY use `--auto`** provided the resolved
  `modelId`/`providerLock` is recorded (commit body + `telemetry/runs.jsonl`),
  while **reviewer/validator seats MUST stay pinned** (a family invariant binds
  there). If an auto executor lands on the same family as a standing validator,
  run the collision guard (swap the colliding validator to a non-colliding
  fallback; fail closed on `unknown`).
- **No Phase-5 inventory:** call `droid exec` directly; do **not** route through
  `tools/exec-cadence.sh` / promote `exec-cadence.md`.
- **Calibration signal:** record `first_seen_in_panel_position` per finding for
  Phase 5 (telemetry/SCHEMA.md).
- If running **unattended**, use bounded rate-limit backoff (~45 min, ~6
  attempts), checkpoint each role call to an on-disk outcome; fail closed on
  non-retryable errors. Still stop at every human gate.

---

## 5. Exit criteria

Read **PRD.md §11 (Phase 3)** for the authoritative list, and §13 for the
efficacy surface. In short: the **full loop on one pilot change** — `/profile`
built; tests independently authored, locked, valid-RED then GREEN; each chunk
ACCEPTED by cross-family validation; the slice landing ACCEPT / ACCEPT-WITH-NITS
— plus the roadmap's **replayable demo** and **baseline comparison** arm. Round
it out with telemetry rows, a `droid-wiki/overview/` Phase-3 entry (template:
`phase-2-planning-slice.md` / `meta-narrative.md`), and a decision packet only
if a chunk hits non-convergence.

---

## 6. Spine to read (hydration order)

1. `PRD.md` — esp. §5.2–5.5 (workflow), §6 (oversight/gates), §9 (artifacts),
   §11 (phase exits — **Phase 3**), §13 (efficacy), §17 (model discipline).
2. `AGENTS.md` — repo operating contract.
3. `droid-wiki/overview/index.md` → `method/workflow.md` → `method/invariants.md`
   → `method/roles-and-models.md`; then `overview/meta-narrative.md` and
   `overview/phase-2-planning-slice.md` for how Phases 1–2 actually ran.
4. `phase-2/README.md` (the accepted brief), `phase-2/plan-v1.md` (what you
   build), `phase-2/findings.md` (amendments A1–A5), `phase-2/KNOWN-ISSUES.md`.
5. `phase-1/` — `run-ledger.md`, `hooks/locked-test-guard.py` (reuse it),
   `build-evidence/` (envelope shape).
6. `telemetry/SCHEMA.md`, `tools/run-with-model.sh`,
   `tools/conventions/*.md`.
7. Pilot: `app.py`, `api/dashboard.py`, `api/accounts.py`, `models.py`
   (`get_user_by_username:568`, schema builders `:114`/`:126`, `_sql:52`,
   seed `:431`), `templates/account_detail.html`, `test/conftest.py`,
   `pytest.ini`.

---

## 7. First-turn actions

1. Hydrate (read the spine). Run `git status` in **both** repos; note the pilot
   is on a detached HEAD with Phase-1 work uncommitted.
2. Re-verify the baseline (`.venv/bin/python -m pytest -q` in the pilot → expect
   87 passing) so you own a known-good starting point.
3. **Confirm the approval record** (`phase-2/APPROVAL.md`, plan-v1 approved and
   bound to `sha256:72eccff5…`). The gate is already PASSED — do not re-ask.
4. Resolve the pilot branch state → create `factory/phase-3-profile` → scaffold
   `phase-3/` (execution brief, reviews/, build-evidence/) → run the per-chunk
   loop in §3, chunk 1 first. If running unattended overnight, apply §4 backoff
   + per-call checkpointing; stop only at the final-merge human gate.

## 8. Do NOT
- Do not re-open the approved plan's decisions (fork (b), no-`?id=`, read-only)
  — they are hash-bound and panel-approved.
- Do not self-approve the plan gate or self-merge.
- Do not let the executor author or edit the tests that judge it.
- Do not start a chunk's implementation before a valid-RED.
- Do not delete/clobber untracked files in either repo.
- Do not promote the parked Phase-5 exec-cadence wrapper.

— handoff authored by the Phase-2 driver; Phase 2 ended at a hash-bound,
cross-family-APPROVED plan awaiting the human gate.

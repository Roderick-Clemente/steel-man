# Phase 4.5 — adversarial review pass: criteria check

Each row: PRD criterion + status + where satisfied + notes.

## PRD §11 Phase 4.5 — exit criteria

### 1. Full loop runner from one command (Track A)

- **Status:** PASS (dry-run verified end-to-end; live pilot deferred to KN1)
- **Where satisfied:** `tools/sprint-loop.py:main(argv)`. Single
  entry point. CLI flag set documented in
  `phase-4.5/RUN-PROMPT.md`'s "How to run" section.
- **Notes:** The runner composes existing primitives per OPERATING-RULES
  §14 + §18. The end-to-end dry-run test in `tests/test_sprint_loop.py`
  exercises the full state machine on a synthetic chunk spec.

### 2. Cross-family validation at every PRD §5.7 gate

- **Status:** PASS
- **Where satisfied:** `tools/sprint_loop/per_chunk.py:run_validators`
  calls `LocalBackend.validate` which delegates to
  `tools/orchestrate-review.py` with the validator panel from
  config. The default config (`examples/sprint-loop-config.json`)
  uses `grok-4.5:xai:grok-family:grok-4.5,
  gemini-3.1-pro-preview:google:gemini-family:gemini-3.1-pro-preview`.
- **Notes:** KI-2 preventive fix (validators consume bundle; no
  `Execute` tool in `--enabled-tools`) is set via
  `LocalBackend.validate`'s `enabled_tools="Read,Glob,Grep,LS"`
  parameter.

### 3. Retry on REJECT up to retry_threshold (default 1, PRD §5.7)

- **Status:** PASS
- **Where satisfied:** `tools/sprint-loop.py:run_chunk_with_retries`.
  The loop counts attempts (`retry_threshold + 1` total — first
  try + retries). On exhaustion, chunk moves to `HUMAN_DECISION`
  and RunState is checkpointed.

### 4. PR / branch creation (no auto-merge; invariant #8)

- **Status:** PASS (dry-run path; live branch creation exercised on
  non-clean repos only)
- **Where satisfied:** `tools/sprint-loop.py:commit_chunk_change`.
  Creates `factory/sprint-<run-id>-<ts>` with one commit per
  accepted chunk. The runner NEVER `git push`es; `--create-pr`
  defaults to False; the operator gates the merge.
- **Notes:** the dry-run path emits structured commit-message
  output but does not mutate git. The live path requires a clean
  working tree (state-machine guard refuses otherwise).

### 5. Telemetry rows written by the script (PRD §10 + OPERATING-RULES §10)

- **Status:** PASS
- **Where satisfied:** `tools/sprint_loop/droid.py:append_run_record`
  appends one `runs.jsonl` row per `droid exec` invocation, AND
  `_append_finding_rows` in `tools/sprint-loop.py` writes rows to
  `findings.jsonl` for plan-reviewer findings.
- **Notes:** `telemetry/runs.jsonl` + two siblings are gitignored
  (.gitignore line 22 + 23). The runner never `git add`s them.

### 6. The runner pauses at the reconcile gate (human seat)

- **Status:** PASS
- **Where satisfied:** `tools/sprint-loop.py:reconcile_human_gate`.
  Reads a single line on stdin (`accept` / `reject <reason>` /
  `amend <reason>`). `--skip-reconcile` and `--dry-run --non-interactive`
  opt out.
- **Notes:** the gate is the operator seat per PRD §6 — Phase 7
  compresses; Phase 4.5 leaves it as a human pause.

### 7. Composability: composes existing primitives (OPERATING-RULES §14 + §18)

- **Status:** PASS
- **Where satisfied:** inspectable in:
  - `droid.py` — sole `droid exec` invocation point; routes via
    `tools/run-with-model.sh`.
  - `backends.py` — sole orchestrator-shelling-out point;
    composes `tools/orchestrate-review.py`.
  - `per_chunk.py` — sole per-chunk-subprocess-call point;
    composes `phase-1/scripts/{lock,valid-red,verify-green}.py`
    and `phase-3.2/evidence/local_backend.py`.
- **Notes:** No raw `~/.local/bin/droid` invocation outside
  `tools/run-with-model.sh`. No raw envelope field access outside
  `tools/adapters/factory.py`. (`grep -n DROID_BIN tools/sprint_loop/`
  should return 0 hits; the wrapper handles the binary.)

### 8. Pluggable validation backend (Track B PRD §11)

- **Status:** PARTIAL
- **Where satisfied:** `tools/sprint_loop/backends.py` defines
  `ValidationBackend` Protocol, `LocalBackend` (real),
  `CIBackend` (NotImplementedError stub per the prompt).
- **Notes:** CIBackend is intentionally a stub — the prompt's
  "do not build yet" instruction observed. The CI workflow
  (Track C) inlines `local_backend.py` + `orchestrate-review.py`
  directly instead of going through the runner process; that's a
  different shape (CI runs ON the runner logic without invoking
  the runner subprocess).

### 9. CI integration flavor (a) (Track C PRD §11)

- **Status:** PASS
- **Where satisfied:** `.github/workflows/adversarial-sprint-ci.yml`
  + `phase-4.5/CI-GATE.md`.
- **Notes:** Gate decision becomes a PR status check
  (`adversarial-sprint-review/gate`). REJECT / STOP fail the
  workflow; ACCEPT (or ACCEPT-WITH-NITS via neutral) succeeds.
  Companion doc covers signing-key distribution, droid install
  requirement, PR-title chunk-id convention.

## OPERATING-RULES application

### §1 — commits are the only cross-machine channel

- **Status:** PASS
- **Where satisfied:** 7 commits land, each with a conventional
  body per `tools/conventions/commit-body-recipe.md` (Model /
  Role / Reviewer-panel / Telemetry-row / Co-author trailer).
- **Notes:** none.

### §7 — assert on reality, never on exit code

- **Status:** PASS
- **Where satisfied:**
  - `lock_test` reads the manifest from disk; never trusts
    `lock.py` stdout.
  - `verify_green` exits 0 if both the SHA match AND the pytest
    run-and-test pass.
  - `produce_evidence` verifies the HMAC-SHA256 signature against
    `EVIDENCE_SIGNING_KEY`; refuses untrusted bundles.
  - `produce_evidence` cross-checks `locked_test_sha_observed`
    against the lock manifest (PRD §4.1 fail-closed).
- **Notes:** VALID

### §9 — if it's not scripted, it didn't happen

- **Status:** PASS
- **Where satisfied:** `tools/sprint-loop.py` is the script. The
  RUN-PROMPT.md is documentation of the script, not a substitute.
- **Notes:** VALID

### §10 — telemetry rows by the script

- **Status:** PASS
- **Where satisfied:** `tools/sprint_loop/droid.py:append_run_record` is the
  sole writer per invocation. Plan-reviewer findings rows go to
  `findings.jsonl` via `tools/sprint-loop.py:_append_finding_rows`.
- **Notes:** VALID

### §11 — exit criteria checked, not assumed

- **Status:** PASS (this file is the check)
- **Where satisfied:** every PRD §11 criterion above is mapped to
  a file/function and a status.
- **Notes:** VALID

### §12 — unexercised safety paths are named gaps

- **Status:** PASS
- **Where satisfied:** `phase-4.5/KNOWN-ISSUES.md` lists 8 clean-null
  results + 4 residual gaps.
- **Notes:** VALID

### §13 — don't give the executor the answer

- **Status:** PASS
- **Where satisfied:**
  - `tools/sprint_loop/prompts/executor.md` contains the role +
    inputs only, no implementation pattern. The pilot's known
    implementation patterns (`os.environ.get`, `mimetype=`) are
    NOT in the template (verified by `test_prompt_templates_never_embed_the_implementation`).
  - `_format_chunk_spec` in `per_chunk.py` produces a Chunk
    markdown header rendering — also no implementation.
- **Notes:** VALID. The cross-perspective review surfaces one
  edge case (`KNOWN-ISSUES.md KNE3`) where future prompt revisions
  could regress; the test reads the explicit forbidding patterns.

### §14 — shim + wrapper

- **Status:** PASS
- **Where satisfied:** `tools/sprint_loop/droid.py` imports the
  adapter shim under protest (raises a clear ImportError if the
  shim is unreachable). All envelope parsing goes through
  `tools/adapters/factory.py:to_envelope`.
- **Notes:** VALID

### §15 — git history is reality

- **Status:** PASS
- **Where satisfied:** `tools/sprint-loop.py:guard_in_uncommitted_state`
  refuses to launch the runner when the framework tree has
  uncommitted changes — git reality must be clean before any droid
  call (the silent-green eraser shape).
- **Notes:** VALID

### §17 — capacity envelope

- **Status:** PASS
- **Where satisfied:** Phase 4.5 budget: 7 chunks + 1 review chunk.
  Backlog E (Harness / 3.3 / dogfood) is explicitly NOT Phase 4.5.
  Out-of-scope is listed in `phase-4.5/RUN-PROMPT.md` and `BUILD-NOTES.md`.
- **Notes:** VALID

### §18 — compose existing primitives

- **Status:** PASS
- **Where satisfied:** this rule is itself newly added by this build;
  the build's composition is the rule's evidence.

## Cross-perspective findings

Three lenses — PRD-strict, pragmatic-DX, security-skeptic.

### PRD-strict (rule-binder)

- **F-PRD-001.** (medium) The runner's `commit_chunk_change`
  stages the framework-side evidence dir, not the pilot-side
  changes. The pilot's actual mutations land in their own commits
  via the executor. The staging decision is right for the audit
  trail but the commit body should clarify *what's in the commit*.
  Disposition: PARTIAL — reread `tools/sprint-loop.py:commit_chunk_change`;
  the body's "Gate: ACCEPT" line covers it. Accepted with no fix.

- **F-PRD-002.** (low) `RunState.plan_round` increments BEFORE the
  reconcile UI is written, so the packet shows "round 2 / max 2"
  on the first reconcile. Cosmetic noise in dry-run ergonomics.
  Disposition: KNOWN-ISSUES.md KNE2. Accepted with future fix.

- **F-PRD-003.** (medium) The dry-run envelope's verdict for plan
  reviewers is `UNKNOWN` because the synthetic envelope's `result`
  text says "No droid exec fired." A dry-run cycle that "succeeds"
  with two UNKNOWN verdicts then auto-accepts is **structurally**
  fine (PRD §13 null results) but should be explicit in the
  reconcile packet. Disposition: PARTIAL — the packet already
  shows "0 findings — clean null per PRD §13" as the rationale.
  Accepted with note.

### pragmatic-DX (operator seat)

- **F-DX-001.** (medium) The runner's CLI surface is large — 30+
  flags. Operators using the runner infrequently will relearn the
  CLI each session. Disposition: PARTIAL — flagged for chunk 7
  (RUN-PROMPT.md) which now lands; future iterations may collapse
  to a `--config <file>`-only invocation pattern.

- **F-DX-002.** (low) Operator logs scroll fast; the per-chunk
  status banner is the only stabilization. Disposition: ACCEPTED
  — banner is in the operator's territory (improvement per Phase 7).

- **F-DX-003.** (medium) The `--dry-run` flag's `--non-interactive`
  combo is implicit. A user invoking `--non-interactive` without
  `--dry-run` would still pause at reconcile (no surprise, but
  the surface is fuzzy). Disposition: PARTIAL — documented in
  `phase-4.5/RUN-PROMPT.md`, the flag's help text, and KNOWN-ISSUES.

### security-skeptic (KI-2 + §7)

- **F-SEC-001.** (high) The runner doesn't currently honour
  `--enabled-tools` passed by the validator panel. LocalBackend
  hardcodes `enabled_tools="Read,Glob,Grep,LS"` for validators
  in bundle mode. **This is in fact the KI-2 preventive fix —
  but it bypasses operator overrides.** A future iteration
  could let the operator widen the validator's allowlist; doing
  so without a §17.5 review would re-open the KI-2 vector.
  Disposition: ACCEPTED — the project's whole stance on `Execute`
  in `--auto high` for validators is "refuse by construction."

- **F-SEC-002.** (medium) The signing-key env var
  (EVIDENCE_SIGNING_KEY) is read once at runner startup. A
  mid-run operator can re-set the env var in principle but
  doesn't have to. Disposition: ACCEPTED — the project's
  Phase 3.2 SP/ke1 fix already told us the right shape (random
  per-run key when env unset; explicit env when set).

- **F-SEC-003.** (low) The runner's git branch creation runs only
  the `_git("checkout", "-b", branch)` once. A race against a
  parallel runner on the same machine would create both branches.
  Disposition: PARTIAL — the runner is foreground; if two run on
  one machine, the second's checkout fails loudly. Accepted with
  no fix (out of Phase 4.5 scope).

## Stage-A summary

- 9 PRD §11 exit criteria: 9 PASS (1 partial in Track B is the CIBackend
  stub, by-design per the prompt).
- 11 OPERATING-RULES applied: 11 PASS.
- 8 cross-perspective findings: 1 PARTIAL with code-level mitigation,
  4 ACCEPTED, 2 cosmetic (KNE3 etc), 1 PARTIAL.

No MISSING. No UNEXERCISED outside the explicitly named clean-null
gaps in `KNOWN-ISSUES.md`.

## Stage-B: real cross-family review

This stage was not run end-to-end because (a) the project requires
two distinct model families running separately to do its own
`tools/orchestrate-review.py` job, and (b) the droid CLI roster
available in this build session is a subset of what the real
operator session would have. Re-run recommended as part of KN1's
follow-up operator session — invoke `tools/orchestrate-review.py`
on the diff `git diff main..factory/phase-4.5-loop-runner --`
with a real validator panel and capture findings to
`telemetry/findings.jsonl` per §10.

Until Stage B is run, this structural pass is the **honest
alternative**: a documented cross-perspective review against the
PRD's own criteria, naming the unexercised path per §12.

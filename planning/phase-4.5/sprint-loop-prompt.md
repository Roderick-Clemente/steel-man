# Phase 4.5 — Full loop runner + CI integration

You are building the product. Phase 4 proved the mechanism and the cost
thesis. But only the review step is scripted — planning, test design,
execution, and reconciliation are still manual `droid exec` calls. This
phase turns the method from a collection of scripts into one command that
runs a complete adversarial sprint.

## Context

The project root is the repository containing `PRD.md` (this file's parent
directory). The pilot repo is at `/Users/factory/work/quantum-bank--llms-txt-pilot`.
Read `PRD.md` §11 Phase 4.5 for the full spec. Read `tools/OPERATING-RULES.md`
for the 17 operating rules. Read `planning/ROADMAP-REVIEW.md` for the project audit.

## What exists today (do not rebuild)

| Component | Script | What it does |
|---|---|---|
| Evidence provider | `phase-3.2/evidence/local_backend.py` | Runs pytest + locked hash + security scan, produces signed EvidenceBundle |
| Evidence consumer | `phase-3.2/evidence/consumer.py` | Validates bundle signature, checks test results, gate decision |
| Orchestrator (review step) | `tools/orchestrate-review.py` | Runs N cross-family validators via droid exec, stray-write check, telemetry, gate decision |
| Valid-RED classifier | `phase-1/scripts/valid-red.py` | Classifies a RED as valid or invalid |
| GREEN verifier | `phase-1/scripts/verify-green.py` | Re-checks locked test hash, verifies GREEN |
| Test locker | `phase-1/scripts/lock.py` | Locks test content by SHA hash |
| Adapter shim | `tools/adapters/factory.py` | Normalizes vendor envelopes to neutral shape |
| Model wrapper | `tools/run-with-model.sh` | Refuses to run droid exec without --model |
| Blind prompt renderer | `tools/render-blind-prompt.py` | Strips executor context from reviewer prompts |
| Telemetry | `telemetry/runs.jsonl`, `telemetry/findings.jsonl` | System of record (34 runs, 71 findings) |

## What does NOT exist (what you are building)

### Track A — Full loop runner

Build `tools/sprint-loop.py` that coordinates all five roles from one command.

**The loop:**

```
1. PLANNER
   - droid exec --model <planner-model> with planning prompt + pilot spec
   - Captures: plan document (hash-bound)
   - Output: plan.md + plan hash

2. PLAN REVIEWER (cross-family)
   - droid exec --model <reviewer-1> with blind plan + review prompt
   - droid exec --model <reviewer-2> with blind plan + review prompt
   - Families must differ from planner (invariant #1)
   - Captures: findings from each reviewer
   - Output: findings.jsonl rows

3. RECONCILE (human gate — stays human)
   - Present findings from both reviewers
   - Wait for human: accept / reject / amend
   - If reject: loop back to planner with feedback
   - If accept: proceed to chunking
   - This step is NOT automated. It is the operator seat.
     Phase 7 will later compress it. For now, the loop runner
     pauses and waits for stdin input.

4. CHUNKING
   - The approved plan is cut into chunks (the planner may do this,
     or the human may do it manually)
   - Each chunk has: scope, observable criteria, commands, rollback,
     evidence requirements
   - Output: chunk list

5. PER CHUNK (the inner loop):
   a. TEST DESIGNER
      - droid exec --model <test-designer-model> with chunk spec
      - Captures: test file + accepted assertion phrase
      - Lock the test: python3 phase-1/scripts/lock.py
      - Run valid-red.py to verify the RED is valid
      - If invalid RED: loop back to test designer

   b. EXECUTOR
      - droid exec --model <executor-model> with chunk spec
        (NOT the solution — per §13, don't give the executor the answer)
      - Executor has implementation write access
      - Captures: diff
      - Run verify-green.py to verify GREEN
      - If not GREEN: retry (up to threshold, per escalation rule)

   c. EVIDENCE PRODUCTION
      - python3 phase-3.2/evidence/local_backend.py
        (produces signed EvidenceBundle)

   d. VALIDATION (cross-family, via existing orchestrator)
      - python3 tools/orchestrate-review.py
        (runs N validators, stray-write check, telemetry, gate decision)
      - Gate: ACCEPT / ACCEPT-WITH-NITS / REJECT / STOP

   e. RETRY/RE-PLAN
      - If REJECT: feed rejection findings back to executor, retry
        (up to retry_threshold, default 1 per PRD escalation rule)
      - If retry exhausted: flag for human decision packet
      - If ACCEPT: proceed to next chunk

6. PR/BRANCH CREATION (the missing Phase 3 exit criterion)
   - Create a local branch: factory/sprint-<timestamp>
   - Commit the changes with a conventional commit message
   - If remote is configured: push and create a PR
   - If not: create a local commit bundle for human review
   - Record the branch/PR in telemetry

7. TELEMETRY
   - Every droid exec invocation appends to runs.jsonl (per §10)
   - Every finding appends to findings.jsonl
   - The loop runner is responsible for telemetry, not the operator
```

**Design constraints:**
- Use `tools/run-with-model.sh` for every droid exec invocation (§14)
- Use `tools/adapters/factory.py` for envelope parsing (§14)
- The loop runner is a foreground process. It pauses at the human gate
  (reconciliation) and waits for stdin. This is NOT "close the laptop" —
  it is "push one button, get paused at the judgment calls."
- The loop runner must be configurable: models per role, pilot repo path,
  test file, lock file, retry threshold, validator count
- The loop runner must handle the case where droid exec fails (provider
  API hiccup, timeout) with retry logic (same pattern as the hardened
  orchestrator)
- Assert on reality (§7/§15): check git state, test results, and envelope
  contents — never trust exit codes alone

**Exit:** `sprint-loop.py` runs the full loop on the QuantumBank pilot from
one command. All five roles coordinated. Human gate at reconciliation.
Retry on rejection. PR/branch created. Telemetry written.

### Track B — Pluggable validation backend

Abstract the local-vs-CI difference. The loop runner calls a validation
backend interface; today it's local, tomorrow it's CI.

```
ValidationBackend (interface):
    def validate(chunk, evidence_bundle) -> GateDecision

LocalBackend:
    - Runs orchestrate-review.py via droid exec
    - Returns ACCEPT/REJECT/STOP from the existing orchestrator

CIBackend (future, just the interface — do not build the CI side yet):
    - Would create a PR, wait for CI status check, read gate result
    - Same interface, different backend
```

This is a small abstraction — do not over-engineer it. The point is that
the loop runner doesn't hardcode `orchestrate-review.py`; it calls
`validation_backend.validate()` and the backend decides how to run it.

**Exit:** `sprint-loop.py` uses `LocalBackend` by default. The
`ValidationBackend` interface exists with a `CIBackend` stub (not
implemented, just the interface). Switching backends is a flag:
`--validation-backend local|ci`.

### Track C — CI integration (flavor a)

Once the loop runner (Track A) and the pluggable backend (Track B) exist,
wire up CI flavor (a): run the evidence provider in a pipeline and gate
on the verdict.

1. **CI workflow file** (GitHub Actions or similar):
   - Trigger: PR opened or updated on the pilot repo
   - Steps:
     a. Checkout the pilot repo
     b. Install dependencies (droid CLI, python, pytest)
     c. Run `local_backend.py` to produce the EvidenceBundle
     d. Run `orchestrate-review.py` to run validators + gate decision
     e. Post gate decision as a PR status check
   - Gate enforcement: REJECT/STOP blocks merge, ACCEPT allows

2. **CI feedback posting:**
   - On REJECT: post the findings as a PR comment
   - On ACCEPT: post a summary (verdict, token count, validator models)
   - On STOP: post an error message with diagnostics

3. **Do NOT build flavor (b) Harness-native yet.** Flavor (a) is
   maximally portable (same script, different environment). Flavor (b)
   is optional and only worth building if Harness extras justify it.

**Exit:** a CI workflow file exists that runs the evidence provider +
validators on a PR and posts the gate decision. REJECT blocks merge.
The workflow is portable (not Harness-specific).

## Operating rules

- Read `tools/OPERATING-RULES.md` before starting. Follow all 17 rules.
- Use `run-with-model.sh` for every droid exec invocation (§14).
- Use `tools/adapters/factory.py` for envelope parsing (§14).
- Assert on reality, never on exit code (§7). Check git history (§15).
- Don't give the executor the answer (§13). The prompt describes the
  problem, not the solution.
- If it's not scripted, it didn't happen (§9). The loop runner IS the
  script.
- Telemetry rows are written by the script, not by the operator (§10).
- Exit criteria are checked, not assumed (§11).
- Unexercised safety paths are named gaps, not phase blockers (§12).
- Commit each track's output as a separate commit with a clear message.

## Suggested order

1. Track A first (the loop runner is the core deliverable)
2. Track B (small abstraction, fold into Track A)
3. Track C (CI workflow, depends on A + B)

Track A is the hard part. Tracks B and C are wiring on top of it.
If Track A is too big for one session, commit what works and hand off
the rest. The loop runner doesn't need to be perfect — it needs to run
the full loop from one command and create a PR. Retry/re-plan edge cases
can be hardened later.

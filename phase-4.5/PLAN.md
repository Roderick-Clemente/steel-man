# Phase 4.5 — Sprint-loop chunk plan

This is the chunk plan for the Phase 4.5 full loop runner + CI integration.
Mirrors the GROK → CHUNK → EXECUTE method in
`templates/SPRINT-PLANNING-TEMPLATE.md`, scoped to **building** the runner
rather than driving it on the pilot.

## Sprint Metadata

- **Sprint Name:** phase-4.5-loop-runner
- **Date:** 2026-08-09
- **Sprint Type:** Build (scripted orchestration + CI wiring)
- **Priority:** P1 — closes the Phase 4.5 PRD §11 deliverable
- **Estimated Duration:** ~8 commits over one or two working sessions
- **Status:** In Progress
- **Branch:** `factory/phase-4.5-loop-runner` (per AGENTS.md author convention)
- **Repro runner:** Python 3.12 (`quantum-bank--llms-txt-pilot/.venv/bin/python`)

## Sprint Principles

- **Script the loop, don't manually paste droid exec.** OPERATING-RULES §9.
- **Assert on reality, not on exit code.** OPERATING-RULES §7.
- **Use the model-discipline wrapper and the adapter shim.** OPERATING-RULES §14.
- **Telemetry rows are written by the script, not by the operator.** §10.
- **Don't give the executor the answer.** §13.
- **Commit each chunk separately.** AGENTS.md commits-are-the-baton.

## Sprint Objectives

### Primary Goal

Co-locate the five Phase 4.5 roles behind one command:
`python3 tools/sprint-loop.py --config <cfg>.json`. The collection of
scripts becomes a runner that pauses at the human reconciliation gate
(stays human), creates a local branch + commit bundle (no auto-merge per
invariant #8), and writes telemetry.

### Success Criteria (PRD §11 Phase 4.5 exit)

- [ ] `tools/sprint-loop.py --help` exits 0 with documented flags.
- [ ] The runner invokes `tools/run-with-model.sh` for every droid exec
      (verified by `grep -n run-with-model.sh tools/sprint-loop.py` ≥ 1).
- [ ] The runner parses every envelope through
      `tools/adapters/factory.py:to_envelope(...)` (verified by `grep -n
      to_envelope tools/sprint-loop.py` ≥ 1).
- [ ] `--dry-run` runs the full state machine without invoking
      `droid exec`, recording planned actions to a JSON plan.
- [ ] At the human reconciliation gate: the runner writes a packet to disk
      and reads `<accept|reject|amend>\n` from stdin.
- [ ] Per-chunk: test_designer → lock.py → valid-red.py → executor →
      verify-green.py → local_backend.py → orchestrate-review.py → gate decision.
- [ ] On ACCEPT for the last chunk: creates a `factory/sprint-<ts>` branch
      with conventional commit bodies (`tools/conventions/commit-body-recipe.md`).
- [ ] On REJECT: feeds rejection back to executor, counts retries, prints
      decision packet when threshold exceeded.
- [ ] `tests/test_sprint_loop.py` exits 0 — config parser, state machine,
      family-guard, retry accounting, and human-gate handshake all covered.
- [ ] Track B interface exists (LocalBackend is real; CIBackend is
      interface-only stub per the prompt's explicit "do not build yet").
- [ ] Track C CI workflow file (`.github/workflows/adversarial-sprint-ci.yml`).
      Workflow YAML parses; `local_backend.py` and `orchestrate-review.py`
      are invoked; gate decision becomes a PR status check.

### Out of Scope

- [ ] End-to-end pilot run (`droid exec` against the QuantumBank pilot
      slice). The framework's null-result rule applies — the unexercised
      path is recorded as a named gap in `KNOWN-ISSUES.md`, not a phase
      blocker (OPERATING-RULES §12).
- [ ] `--mission` re-litigation. Phase 0 GO-NO-GO closed Mission-native
      permanently.
- [ ] `--validation-backend=ci` runtime implementation. Per the prompt,
      the CIBackend is interface-only; the local path is the working path.
- [ ] Harness / 3.3 visual tier / framework-repo dogfood (Backlog E).

## Stage 1 — GROK (problem analysis)

### Current state

- `tools/orchestrate-review.py` runs the existing review step but only
  the review step.
- `phase-3.2/evidence/local_backend.py` produces a signed EvidenceBundle.
- Planning, test design, execution, reconciliation, and PR creation are
  still manual `droid exec` calls.

### Root cause / opportunity (PRD §1, §11 Phase 4.5)

The method is a collection of scripts. The Phase 4 PRD §15 Act 2
promise ("push a button, get a sprint") requires a single command that
runs the loop. Without it, every operator run is fragile, slow, and
loses the §17 model-discipline guarantees whenever the operator is
tired.

### Risk assessment

| Risk | Sev | Probability | Impact | Mitigation |
|---|---|---|---|---|
| Runner becomes a meta-script with no real safety | H | M | Bypasses §7 reality-assert, KI-2 | Runners asserts on git history + bundle sig + verify-green.py exit |
| False green: pipeline reports success while nothing happened | H | M | Silent-green-class defect; PRD §13 invalidated | Every checkpoint reads real artifacts (SHA, signed bundle, pytest results) |
| Operator gets droid-blind paste suggestion via defaults | M | L | Loses invariant #1 if `--auto` slips through | `run-with-model.sh` wrapper is the gate; default `--model` is loud-mandatory |
| Human gate silently skipped | M | L | Reconciliation = operator's seat per PRD §6 | Pauses on stdin; skipped = explicit flag (`--skip-reconcile`); logged in telemetry |
| Cross-family separation bypassed via `--auto` on reviewer/validator | M | M | Same defect the §17 rule prevents | Reviewer/validator seats set their `--model` from config; `FamilyGuard` raises on collision with planner/executor (configurable exception in KNOWN-ISSUES only) |
| Telemetry rows accidentally staged | H | M | §17.4 violation, history-travels leak | Rows appended with `git status` post-write baseline exclusion; runner does not `git add` telemetry paths |
| `--validation-backend=ci` invoked without a built impl | M | L | Operator surprised by NotImplemented exit | CIBackend is a stub that raises with a clear "use --validation-backend=local" message; never falls through silently |
| End-to-end pilot not run in this commit | M | H | "Replayable demo" PRD §11 exit criterion unmet | Recorded as named gap in KNOWN-ISSUES.md; clean-null result per §13 |

## Stage 2 — CHUNK plan

Each chunk is a separate commit; commits are the baton (AGENTS.md).
Reviewer pauses at chunk boundaries via the planning-templated review +
conventional commit body (`tools/conventions/commit-body-recipe.md`).

## Principle: compose existing tools, do not reinvent

The runner is **thin orchestration on top of the primitives the project
already ships**:

| Existing primitive | Path | What the loop runner does with it |
|---|---|---|
| `tools/run-with-model.sh` | bash wrapper | Every `droid exec` in the loop is routed through it (OPERATING-RULES §14) |
| `tools/adapters/factory.py:to_envelope` | vendor shim | Every envelope is parsed via it; never raw field access (§14) |
| `tools/render-blind-prompt.py` | blind-prompt renderer | Used to strip executor context from reviewer prompts (existing privacy invariant) |
| `tools/orchestrate-review.py` | orchestrator (review step) | Per-chunk validation step calls this directly with chunk-specific args |
| `phase-3.2/evidence/local_backend.py` | evidence producer | Per-chunk, after GREEN, shells out to it to produce a signed `EvidenceBundle` |
| `phase-3.2/evidence/consumer.py` | bundle consumer | Optional dry-run gate check before invoking validators |
| `phase-1/scripts/lock.py` | test locker | Per-chunk, after test_designer writes the test |
| `phase-1/scripts/valid-red.py` | valid-RED classifier | Per-chunk, after lock — confirms RED is for the intended reason |
| `phase-1/scripts/verify-green.py` | GREEN verifier | Per-chunk, after executor writes the implementation |

The runner's NEW code is the **state machine + retry accounting +
human-gate handshake + telemetry + branch/PR creation + config parser +
Track B interface**. None of these exist yet. Everything else is composed.

## Chunk plan (revised — composes existing tools)

Each chunk is a separate commit. Each chunk is verifiable at commit time
(OPERATING-RULES §11).

| # | Chunk | Commit subject | What's reused | Tests touched |
|---|---|---|---|---|
| 1 | `tools/sprint_loop/{__init__,state,config}.py` + `tests/test_sprint_loop.py` + `tests/pytest.ini` | `phase-4.5: chunk 1 — state machine + config + tests` | nothing (pure data) | tests/test_sprint_loop.py (config parse, state transitions, family guard, retry math, gate embed) |
| 2 | `tools/sprint_loop/droid.py` (model-discipline wrapper) + `tools/sprint_loop/backends.py` (Track B: LocalBackend shells out to orchestrate-review.py; CIBackend stub) | `phase-4.5: chunk 2 — droid wrapper + validation backends` | `tools/run-with-model.sh`, `tools/adapters/factory.py`, `tools/orchestrate-review.py` | tests for droid wrapper (run subprocess mock), backends (subprocess stub) |
| 3 | `tools/sprint_loop/prompts/` (5 role prompt templates, pluggable) | `phase-4.5: chunk 3 — role prompt templates` | `tools/render-blind-prompt.py` (blind-reviewer rendering) | tests for prompt-template substitution |
| 4 | `tools/sprint_loop/per_chunk.py` (inner loop: test_designer → executor → evidence → validation → retry; composes existing scripts) | `phase-4.5: chunk 4 — per-chunk inner loop` | `phase-1/scripts/lock.py`, `valid-red.py`, `verify-green.py`, `phase-3.2/evidence/local_backend.py`, `phase-3.2/evidence/consumer.py`, `tools/orchestrate-review.py` | tests for state transitions within per-chunk + retry math |
| 5 | `tools/sprint-loop.py` (top-level orchestrator: planner → plan-reviewer → reconcile gate → chunking → per-chunk loop → PR/branch) | `phase-4.5: chunk 5 — runner orchestrator` | every tool from chunks 1–4 | tests for top-level state machine + reconcile handshake (stdin mock) |
| 6 | Track C — `.github/workflows/adversarial-sprint-ci.yml` + `phase-4.5/CI-GATE.md` | `phase-4.5: chunk 6 — CI flavor (a) workflow + companion doc` | reuses the runner's calling convention from chunks 1–5 (CI is just --validation-backend=local with GH-Actions trigger) | yaml.safe_load smoke; manual narrative review |
| 7 | `phase-4.5/RUN-PROMPT.md` + `examples/sprint-loop-config.json` + `examples/sprint-loop-chunks-example.json` + `phase-4.5/ASSUMPTIONS.md` + `phase-4.5/KNOWN-ISSUES.md` + `phase-4.5/BUILD-NOTES.md` + adversarial review pass against PRD §5.2/§5.4/§5.5/§5.6/§5.7/§5.8 | `phase-4.5: chunk 7 — docs + adversarial review pass` | reusable spec | inline review notes + an `adversarial_review/` find/scope loop |


## Stage 3 — Plan acceptance

- Sprint objectives match the Phase 4.5 PRD exit.
- Chunk ordering chunks the hard parts (state + backend interface) before
  the orchestrator (so the orchestrator has real types to call into).
- Each chunk has a verifiable, script-runnable check at commit time
  (OPERATING-RULES §11 — exit criteria are checked, not assumed).
- The runner is bounded (OPERATING-RULES §17 — refuse unbounded foundation
  programs): one phase, four tracks in PRD §11 Phase 4.5, no scope creep.

## Operating-rules application summary

| Rule | How this chunk plan applies it |
|---|---|
| §6 scope shifts explicit | Any chunk that absorbs a new sub-deliverable logs the shift here + in ASSUMPTIONS.md |
| §7 assert on reality | Runner asserts on bundle signature, locked-SHA, pytest results, git history — never trust exit codes alone |
| §9 scripted, not manual | The script is the default; RUN-COMMANDS is documentation only |
| §10 telemetry by script | Every droid exec appends to runs.jsonl inside the loop; never copy-paste after the fact |
| §11 exit criteria checked | Chunk 7 includes a self-check against the success criteria in this doc |
| §13 don't give the executor the answer | Executor role prompt template contains only the chunk spec + acceptance criteria, not the implementation |
| §14 shim + wrapper | All droid calls via `run-with-model.sh`; all envelope parsing via `tools/adapters/factory.py` |
| §15 git history is reality | Runner asserts on `git rev-parse HEAD` and `git status --porcelain` to confirm branch moved |
| §16 demo claims | The "push a button" claim is bounded by what's been scripted; never claim Mission capabilities |
| §17 capacity envelope | One bounded phase; refuse to add tracks that aren't in PRD §11 Phase 4.5 |
| **§18 compose / chunk / fix friction / review / distill** | Chunk 1's RUN-PROMPT-shaped table at top of doc; the runner is thin composition on existing primitives; the runner's friction surfaces inline §13-like fixes (e.g. `run-with-model.sh` now refuses `--mission`); the build is committed chunk-by-chunk with a check at each boundary; the adversarial review at the end of the build writes findings to `phase-4.5/adversarial_review/` |


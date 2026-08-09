# Phase 4.5 — adversarial panel input request

The build session has reached a place where four structural
decisions deserve an outside read. The panel is asked to read each
and respond with ACCEPT / ACCEPT-WITH-NITS / REJECT / HUMAN_DECISION
plus a one-paragraph rationale and any concrete fix. Cross-family
input is the goal — at minimum two distinct model families
participating, ideally. Single-family pass **still** produces
useful input but is named as a clean-null per PRD §13.

## Scope of review

The panel is asked to review the *commit series* on branch
`factory/phase-4.5-loop-runner`. Diff size: 9 commits, ~110 KB
across 33 files. Commits in chronological order:

```
758c349 phase-4.5: chunk 9 — final exit-criteria self-check + rehydration step
0889296 phase-4.5: chunk 8 — adversarial review pass + skill digest
87271eb phase-4.5: chunk 7 — RUN-PROMPT + ASSUMPTIONS + KNOWN-ISSUES + BUILD-NOTES
825fa0c phase-4.5: chunk 6 — CI flavor (a) workflow + companion doc
489b673 phase-4.5: chunk 5 — runner orchestrator + examples + integration tests
969fcbd phase-4.5: chunk 4 — per-chunk inner loop composing existing primitives
caba6cd phase-4.5: chunk 3 — role prompt templates + pluggable renderer
011362d phase-4.5: chunk 2 — droid wrapper + validation backends (Track B)
8f5ecda phase-4.5: chunk 1 — state machine + config + tests + §18 operating rule
```

READ ONLY. No `Execute`, no `Edit`. Do not modify the tree.

## Decisions to weigh in on

### Decision 1 — Family guard widening (state.py)

**Widen OR DO NOT WIDEN** the §4 family guard from "binding seats
only" to "ANY role family=unknown fails closed."

- **Current state:** `check_family_separation()` in
  `tools/sprint_loop/state.py` does two checks:
  (a) binding-seat collisions across PLAN_REVIEWER, TEST_DESIGNER,
      VALIDATOR refuse (PRD §17.2 narrow sense),
  (b) ANY role's `pinned_family` resolved to `"unknown"` (i.e.,
      not in MODEL_FAMILY_MAP) => fail closed.
- **Origin:** This started as (a) only. The user-prompt test for
  "unknown model family" surfaced the gap: an operator pointing
  the runner at a model whose family isn't curated would *enter
  the gate* and fail *during* validation, not at config-load.
- **Why I'm defending it:** PRD §4 names provenance as a hard
  rule for "all model selections." A binding-seat-only guard reads
  like (a) it (narrow) was good enough; reading §4 strictly, it's
  not.

Open questions:
- Does §4 really apply to executor / planner too, or is the §17.2
  carve-out for non-binding seats a deliberate relaxation?
- Is widening worth breaking any existing config that pointed an
  executor at an out-of-map model, or are those configs unreachable
  anyway (because the model installs a `droid` flavor which the
  runner expects to call)?

### Decision 2 — Skill three-layer hybrid (skills/adversarial-sprint/SKILL.md)

**APPROVE OR FLAG CHANGES** to the three-layer hybrid:
digest (compaction-durable) + index (one-file-read) +
rehydration (long-job loop).

- **What it does:** When a long-context droid session loses
  references during compaction, the skill body still carries
  ~300 tokens of load-bearing principles. Index points at full
  §1–§18 in `tools/OPERATING-RULES.md`. Rehydration step says:
  re-read the rule file when conversation crosses ~150k tokens,
  before a new chunk, on §13 disambiguation, or operator re-points.
- **Why it isn't just references:** a pure-reference skill would
  pass the "lightweight" criterion but survive only as long as the
  agent hasn't compacted. Index-only is fragile. Bake-it-in
  bakes even the rules the agent doesn't need into every prompt.
  The hybrid is the only one that survives the actual constraint.

Open questions:
- Are 7 digest principles the right number, or does the panel
  prefer a smaller / larger set?
- Is ~150k tokens the right rehydration trigger, or should it be
  a different signal (e.g., chunk boundaries)?

### Decision 3 — §18 added to OPERATING-RULES.md

**APPROVE / REJECT** the §18 addition: compose existing primitives,
build in chunks, fix ergonomic friction inline, review at the
end, distill reusable principles.

- **Origin:** §18 is itself the distilled principle from the
  build. Earlier behavior was "rebuild from scratch" which
  violates the project's own §14 (`shim + wrapper`) and §17
  (capacity envelope). The new rule names the underlying
  commitment.
- **Why I'm defending it:** the build's own evidence supports
  it — this branch composed `lock.py / valid-red.py / verify-
  green.py / local_backend.py / orchestrate-review.py /
  run-with-model.sh / adapters/factory.py` rather than
  reinventing. Adding the rule formalizes that.

Open questions:
- Is naming these five sub-rules an effective operating rule, or
  is it too prescriptive? The sub-rules could be one rule with
  five examples instead.
- Should §18 be tagged "promoted-from-build-evidence" so future
  agents understand it's not foundational?

### Decision 4 — Reconcile gate = stdin pause, NOT auto-accept

**APPROVE / REJECT** the choice that the runner pauses for human
at the plan-review reconcile, even after both reviewers ACCEPT.

- **What it does:** `tools/sprint-loop.py:reconcile_human_gate()`
  reads a single line on stdin (`accept` / `reject <reason>` /
  `amend <reason>`). The runner does NOT auto-accept on dual
  ACCEPT to fast-batch the operator's workflow.
- **Why I'm defending it:** The PRD §6 names the human seat at
  phase boundaries. Plan-review revoke is exactly such a
  boundary. Auto-accept would compress the Phase 6 primitive
  prematurely.

Open questions:
- Is stdin-pause the right UI, or should the runner respect a
  `--accept-on-dual-accept` flag for batch runs?
- If the operator wants to fast-batch, where should that flag
  live (runner vs. per-chunk config)?

## Method of response

The panel's model emits the verdict in the *last line* per the
project's `orchestrate-review.py` term pattern. Last line of the
text response must be one of:

```
ACCEPT-WITH-NITS  |  ACCEPT  |  REJECT  |  REJECT_TEST  |  REJECT_IMPLEMENTATION  |  HUMAN_DECISION
```

Rationale and concrete fix proposals go in the body. Read-only mode
is binding — `Execute` will not be enabled. Stray-write check is
applied to this prompt's behavior: a panel member that emits any
non-text response that writes to disk outside `phase-4.5/build-
evidence/r-panel-<label>/` is failing a KI-2 condition.

## Sufficient evidence

- `phase-4.5/PLAN.md` — intent
- `phase-4.5/RUN-PROMPT.md` — operator surface
- `phase-4.5/ASSUMPTIONS.md`, `KNOWN-ISSUES.md`,
  `BUILD-NOTES.md` — gap log
- `phase-4.5/CI-GATE.md` — Track C (a) flavor
- `phase-4.5/adversarial_review/criteria-check.md` —
  the build session's own structural review pass
- `phase-4.5/adversarial_review/findings.jsonl.schema.md` —
  Dispositions
- `tools/sprint_loop/state.py`, `config.py`, `droid.py`,
  `backends.py`, `per_chunk.py` — code
- `tools/sprint-loop.py` — orchestrator
- `tools/OPERATING-RULES.md` §1–§18 — operating rules
- `skills/adversarial-sprint/SKILL.md` — the asset under review
- `tools/sprint_loop/prompts/{planner,plan-reviewer,test-
  designer,executor,validator}.md` — role prompts
- `tests/test_sprint_loop.py` — 56 tests covering the build

Don't read the diff in detail — the criteria-check.md already
maps PRD §11 exit criteria to file paths. Focus on the four
decisions.

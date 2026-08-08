# Roadmap Review — RUN PROMPT

You are the **orchestrator** for a full roadmap review of the adversarial-sprint
project. The goal is not to build anything — it is to audit what has been built,
identify missed wins, and propose where the roadmap should go next.

## What to do

### Phase 1: Hydrate (do this yourself)

Read the following to understand the full arc:

- `PRD.md` — the product requirements document (all sections, especially §13
  evaluation, §15 demo narrative, §16 open decisions, §17 model discipline)
- `tools/OPERATING-RULES.md` — the operating rules (especially the new §8 on
  scope shifts)
- `tools/README.md` and `tools/adapters/factory.py` — the adapter shim architecture
- `telemetry/SCHEMA.md` — the data schema (now v2)
- Every phase directory's README / RESULTS / BUILD-NOTES / ASSUMPTIONS:
  - `phase-0/` — feasibility spike
  - `phase-1/` — test-evidence vertical slice
  - `phase-2/` — brief + plan approval
  - `phase-3/` — execute the sprint (3 chunks, full adversarial loop)
  - `phase-3.1/` — degraded loop spike (RESULTS.md)
  - `phase-3.2/` — evidence provider (BUILD-NOTES.md, ASSUMPTIONS.md)
  - `phase-3.3/` — visual/behavioral tier (SPIKE.md only, seed)
- `telemetry/runs.jsonl` — the actual cost data (gitignored, local only)

### Phase 2: Dispatch sub-agents to audit each phase

Launch **one explorer sub-agent per phase** (Phase 0 through 3.2). Each
sub-agent's job:

> Read the phase's directory, its evidence, its results, and its known issues.
> Answer three questions:
> 1. What was supposed to be built? (per the phase's RUN-PROMPT / spec)
> 2. What was actually built? (per the evidence / code / results)
> 3. What was missed? — obvious wins, gaps, things that should have been
>    scripted but weren't, things that were done manually that should have
>    been automated, scope shifts that weren't named.

Each sub-agent returns a concise findings document. The orchestrator collects
all of them.

### Phase 3: Synthesize

From the sub-agent findings + your own hydration, produce:

1. **What's been done** — a concise table: phase, objective, status, key
   finding/lesson.
2. **What's next** — the current roadmap as written (3.2 follow-on → Harness →
   H-CI experiment → 3.3 → framework dogfood).
3. **Missed wins** — gaps that were discovered late (like the orchestration
   script), things that should have been scripted but weren't, process
   improvements that fell through the cracks.
4. **Roadmap proposal** — where SHOULD the roadmap go? Challenge the current
   sequencing. Are we building the right things in the right order? What
   obvious wins are we leaving on the table? What would a different ordering
   unlock?
5. **Process improvements** — what rules should be added to
   `tools/OPERATING-RULES.md` based on what we've learned?

### Phase 4: Write the output

Write `ROADMAP-REVIEW.md` in the repo root with all of the above. This is a
planning artifact, not code. It goes to the human for review.

## Guardrails

- **Read-only.** Do not modify any code, spec, or existing artifact. The only
  file you write is `ROADMAP-REVIEW.md`.
- **Be honest.** The PRD says "honest technical assessment, including
  unflattering findings" belongs in the record. If a phase was over-engineered,
  under-scripted, or missed an obvious win, say so.
- **Challenge the sequencing.** The current roadmap was written before any of
  this was built. Now that we have data, does the sequencing still make sense?
  Should automation (Act 2) come before more evidence-tier work (3.3)? Should
  the H-CI experiment come before or after the Harness backend?
- **Don't propose building.** This is a review, not a build. Propose what
  should be done, don't do it.
- **Use the scope-shift rule (§8).** If you find scope shifts that weren't
  named during a phase, call them out. That's the kind of gap this review
  exists to find.

## Definition of done

`ROADMAP-REVIEW.md` exists, covers all 5 sections, cites specific evidence
from the phase directories, and is presented at the human gate.

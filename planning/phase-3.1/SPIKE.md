# Phase 3.1 — Spike: budget-degraded loop (cheap test-author + executor, frontier validation only)

**Status:** COMPLETE. Ran on `factory/phase-3.1-degraded` (isolated worktree at
pilot base `8a10711d`); presented at the human merge gate, **not merged**. Full
write-up with numbers: `phase-3.1/RESULTS.md`. The full-invariant baseline (the
control arm) is recorded in `telemetry/runs.jsonl` (~541k tokens total).
Execution handoff was `phase-3.1/RUN-PROMPT.md`.

## Origin

During Phase 3 execution, frontier models were temporarily unavailable (~37 min
rate-limit window). The question arose: can Droid Core (or similar cheap-tier)
fill the test-author and/or executor seats when frontier models are exhausted,
with frontier models used only for cross-family validation? This is the
"token window" scenario — the framework hits a budget or availability wall and
must decide: stop (invariant #7, explicit degradation) or degrade gracefully?

## Hypothesis

When frontier models are unavailable, a degraded loop using a single cheap-tier
model family for **both** test-authorship and execution, with frontier models
restricted to cross-family validation only, can still produce acceptable-quality
code — **provided** the frontier validators catch enough same-family biases
from the diff alone to compensate for the lost test-independence backstop.

## What it tests

- **Invariant #1 degradation:** test-author = executor family is the exact
  failure mode the framework exists to prevent. The spike measures whether
  cross-family validation alone (without independent test authorship) is
  sufficient to catch the resulting blind spots.
- **Invariant #7 boundary:** where does "stop rather than silently weakening"
  give way to "degrade with a recorded exception"? The current answer is "stop."
  This spike asks whether a documented, measured degradation is ever acceptable.
- **Cost/quality tradeoff (H3 adjacent):** if the degraded loop produces code
  that passes the same acceptance tests, the cost savings of cheap-tier
  test-authorship are real. If it doesn't, same-family test-authorship is a
  hard floor, not a tunable knob.

## How to run it

1. Re-run the same `/profile` slice (or a comparable one) from an identical
   pilot snapshot.
2. Seats:
   - Test-author + executor: the **same** cheap-tier model (e.g., Droid Core /
     GLM-5.2, zhipu family).
   - Validators: `grok-4.5` (xAI) + `gemini-3.1-pro-preview` (google) —
     unchanged from Phase 3.
3. Everything else identical: same plan, same chunk structure, same lock/RED/
   GREEN/validate cycle, same accepted assertions.
4. Compare against the Phase 3 baseline:
   - Did the same-family tests encode biases the validators caught?
   - Did the validators' findings differ in count, severity, or category?
   - Did the final code pass the same acceptance criteria?
   - What was the token cost delta?

## What the results told us (OBSERVED — see `phase-3.1/RESULTS.md`)

The outcome was **neither** clean graceful-degradation **nor** a plain hard
floor — it was **panel-dependent**, which is a more useful answer than either
hypothesis predicted:

- The same-family author encoded the expected test-independence bias in **1 of 3
  chunks** — chunk 1, the read-model test, which omitted the standalone
  DB-seeding fixture the frontier control included. Chunks 2–3 (which used the
  `client` fixture) matched the control with 0 findings.
- **Validators split on it:** `grok-4.5` caught it (`REJECT_TEST`, correctly
  attributed to the test); `gemini-3.1-pro-preview` observed the identical
  standalone failure in writing but dismissed it and returned `ACCEPT`. So
  **frontier validation *alone* did not reliably compensate** — a single-gemini
  config would have shipped the weakened test. A **multi-model panel with
  any-reject-blocks did** compensate.
- Independently, the **family-blind deterministic gate** (`verify-green.py`,
  standalone) caught it every time and is the cheapest, most reliable backstop.
- After **one capped test-author retry** fed the cross-family finding, the cheap
  seat restored independence (a `tmp_path` + `init_db()` fixture, arguably more
  robust than the control's) and the panel reached unanimous ACCEPT.

**So the documented fallback is conditional, not free:** cheap same-family
authorship is acceptable *only* paired with (a) a deterministic standalone test
gate and (b) a ≥2-model fail-closed validation panel with mandatory
retry-on-reject. Drop either backstop and the degradation is silent. Cost was
~2.38x the control, but roughly half of that is the rejection+retry cycle, and
cross-family token sums are noisy (KI-3 accounting); the real lesson is
structural — the degraded loop only saves money if it passes first try.

This feeds Phase 5 calibration and the §13 efficacy surface as evidence, not
intuition: same-family authorship raised the blocking-finding rate from 0 → 1
across three chunks, concentrated entirely at the model-layer/no-fixture seam,
and the catch was 1-of-2 (panel size and fail-closed semantics are load-bearing).

## Relationship to Phase 3

Phase 3 must complete first with the full invariant set intact (frontier
test-author, cheap executor, frontier validators). The Phase 3 baseline is the
control arm for this spike. Running 3.1 before 3 invalidates the comparison —
there is no clean baseline to measure against.

## Open questions

- Should the degraded loop record an explicit "degradation exception" in the
  run artifact, or is the model-seat table sufficient?
- Is one cheap model family filling both seats, or should they be different
  cheap families (if available)? The former tests the worst case; the latter
  tests a middle ground.
- Does the spike belong in the §13 efficacy evaluation, or is it a separate
  operational resilience measurement?

---

## Related but distinct: per-seat fallback registry (resilience, NOT a panel)

**Origin.** During Phase 3 chunk 1 the planned openai executor tier
(`gpt-5.4-mini`) was down for hours (KI-1). The human approved substituting
`glm-5.2` (zhipu). It worked and chunk 1 reached cross-family ACCEPT. The
question raised: make model-substitution "part for the course" — a first-class
mechanism rather than an ad-hoc decision.

**The idea.** A small, ordered **fallback registry per seat**: each seat lists
candidate model IDs with family tags; the orchestrator resolves the first
*available* candidate that still satisfies the seat's separation constraints,
reusing the existing collision guard (fail closed on `unknown`). Example:

```
executor:   [gpt-5.4-mini(openai), glm-5.2(zhipu), <deepseek?>]
validator:  [grok-4.5(xai), gemini-3.1-pro-preview(google)]  # pinned, no auto-fallback
```

**Why this is easy and worth doing:** it exercises the collision guard against a
*real* outage instead of the synthetic `--model auto` proxy Probe 2 used, and it
turns "the run stops because one provider is down" into "the run picks the next
compliant model and records the swap."

**Important boundary — this is NOT the review panel.** Two different seats, two
different purposes; conflating them would weaken the method:

- **Executor fallback = resilience / cost.** The executor is the seat where *no*
  family invariant binds beyond pairwise separation (§17.1). Multiple executor
  candidates buy availability and cost-tiering, **not** independence. Adding
  models here does not make the code more trustworthy.
- **Review panel = independence.** The validator/reviewer seat is where family
  multiplicity buys uncorrelated blind-spot coverage (the Phase-6 thinking-hats
  concept). That is the "panel," and it belongs at the review seat only.

So the fallback registry should ship as an **operational resilience feature**
under model-discipline, explicitly *not* branded as "the first part of the
panel." Validator seats stay pinned (a family invariant binds them); only the
non-separation-critical seats (planner, executor) get auto-fallback.

**Open question for the registry:** where does the candidate list live and who
owns it? Natural home is alongside `model-families.json` (same curation +
review-date discipline), since availability and family provenance are both
hand-maintained facts the resolver needs.

# Phase 3.1 — Spike: budget-degraded loop (cheap test-author + executor, frontier validation only)

**Status:** NOT STARTED. Recorded as a future spike during Phase 3 prep on
2026-08-07. Do not run during Phase 3 — Phase 3 must demonstrate the full
invariant set intact first.

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

## What the results would tell us

- **If validators catch the biases:** the loop has a graceful degradation path
  for budget-constrained runs. The frontier-only-validation configuration is a
  documented fallback, not a violation. This is operationally valuable: it
  means the framework doesn't hard-stop every time a frontier model is
  rate-limited.
- **If validators miss the biases:** same-family test-authorship is a hard
  floor. The framework must stop (invariant #7) when it cannot seat an
  independent-family test-author. The cost of that guarantee is recorded
  honestly.
- **Either way:** the result is evidence, not intuition. It feeds Phase 5
  calibration and the §13 efficacy surface.

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

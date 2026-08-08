# Human-in-the-loop compression

The method's cost model tracks credits and tokens. It does not track the operator. This page is about the seat the framework keeps for a human, why that seat gets *more* expensive as you run more loops, and the Phase 7 plan to compress it without breaking the independence that makes the loop work. It is forward-looking: none of it is built, and the pain it addresses has to be measured before it can be sized.

## The problem: the loop moves human effort, it does not remove it

Every loop you take off your plate you replace with supervision. The bottleneck moves from *writing the code* to *adjudicating the handoffs*, and there are two handoffs where a human currently sits:

- **Reconciliation tie-breaks.** One plan, plus a reviewer from a different family attacking it. The human walks the critique list and rules accept / reject / amend on each.
- **Decision packets** ([Phase 2](overview/phase-2-planning-slice.md)). A genuine judgment call, with context the human has to reload each time.

Writing code is bounded and legible, you can see the diff. Adjudicating is unbounded, and a decision packet is the worse of the two because it is judgment, not a pre-formed list. Both seats are **O(n) in the number of concurrent loops**. Run 30 loops and you are busier than ever: the operator, not the model, is now the shared resource all 30 contend for.

That is a structural ceiling, and it is the same style of argument the rest of the project rests on. It is independent of model quality. A smarter model does not remove the seat; it just produces more work to adjudicate. So "point the loop at any project, minimal input" is false as long as the human seat scales with the number of loops.

This is recorded as a **finding to be measured**, not a claim already proven. The §13 efficacy surface measures credits and tokens; operator-minutes is the axis that just went up, and it is not on that surface yet.

## The reconciliation seat is the good case

Reconciliation is not arbitration between two whole plans. It is *one plan plus a list of critiques*, and each critique is a discrete accept / reject / amend decision. That structure matters:

- it is **batchable** in a way that "hold two plans in your head" is not;
- the human cost is not O(number of critiques), it is O(number of *real* disagreements), which is much smaller, because most critiques are cheap and only a few are genuinely contested;
- it is a natural place for a third-family reconciler to triage, auto-resolving the obvious ones and escalating only the genuine conflicts.

The decision-packet seat is the harder one, because it is a judgment call rather than a ruling on a pre-formed list. Phase 7 attacks the reconciliation seat first for that reason.

## The bet: compress the seat without breaking invariant #1

The goal is to move the human from "read every finding" to "rule only on genuine disagreement". Four mechanisms, all sitting on machinery that already exists (`telemetry/findings.jsonl`, `telemetry/aggregate.py`, and the self-declared-risk input from [Probe 8](probes/probe-8-self-declared-risk.md)):

### A panel, with hats assigned across families

A review **panel** instead of a single reviewer, with thinking-hats-style lenses (caution, facts, alternatives, and so on). The critical constraint: **hats are lens diversity, not source diversity.** Six hats on one model are one opinion in six costumes, which is exactly the failure [invariant #1](method/invariants.md) warns about ("two passes from one family are one opinion twice"). So hats do not replace family separation, they layer on top of it: assign the hats *across* families so you get both axes at once. Family stays the independence control; the hat is a guaranteed-coverage checklist that forces someone to always do caution, always do facts.

This formalises the calibration-divergence signal the project already sees. Today "Gemini caught the hook-security family, Grok caught the rubric family" (Phase 1), and the mirror of it on planning artifacts in [Phase 2](overview/phase-2-planning-slice.md), is a happy accident of what each model attends to. Hats turn the accident into an assignment: you force coverage of the finding-types instead of hoping the panel happens to span them.

### An escalation knob that gates on disagreement, not volume

You do not want "tag me on every finding". You want "tag me when the panel *cannot* resolve it itself". The knob's tag-in triggers are things like: the panel splits above a threshold, a finding lands above a severity or risk bar, or two hats produce a conflict a reconciler cannot collapse. Everything the panel agrees on flows through; only genuinely contested calls reach the human. That is the O(critiques) → O(real disagreements) compression made into a configurable dial.

### Panel size scaled by stakes

The same tiering the executor already uses, applied to review. A panel multiplies review spend, so it is not worth it on simple code. The routing signal already exists: the chunk's self-declared risk ([Probe 8](probes/probe-8-self-declared-risk.md)) plus its declared complexity ceiling. Low risk and low complexity gets one cross-family reviewer or none; only high-stakes work convenes the full hatted panel. Panel size becomes a function of stakes, not a fixed cost paid on every diff.

### Calibration telemetry over time

Track which hat/family seat catches which finding-family, its hit rate, and its unique-vs-overlap contribution, in `telemetry/findings.jsonl` aggregated by `telemetry/aggregate.py`. Over enough runs that tells you which seats earn their tokens and which are dead weight, and you prune. The marginal cost of a second reviewer on a small slice (~250k–500k tokens) stops being a vibe and becomes a keep/cut decision.

## The guard: consensus is not correctness

A wider panel can manufacture false comfort. A panel that agrees can be confidently wrong together, and that agreement can pull the operator out of the loop exactly when they should be in it. So the calibration record has to include **panel-agreed-but-wrong** cases, caught later, or the knob will happily tune the human toward less intervention on the basis of agreement that was never evidence.

This is the project's founding principle turned on the panel itself: [a run's own account of itself is not evidence](findings/silent-green.md). The same skepticism applied to the executor's green check has to apply to the panel's consensus.

## Status and placement

This is **Phase 7** in `PRD.md` §11: post-MVP, pain-point-driven, and deliberately kept **outside the measured 0–6 arc**. The reasoning is in the [roadmap](overview/index.md#roadmap): Phases 0–4 are the MVP, the point at which the core loop runs end-to-end and the §13 comparison produces a measured result. Phase 5 generalises across stacks and Phase 6 hardens the loop's own invariants at no new behaviour. Phase 7 is different from both: it is new behaviour aimed at the *operator's* cost, and it is gated behind actually running the MVP and hitting the operator-bottleneck for real.

Its efficacy is its own measurement (operator-minutes per landed change, tag-in rate, panel calibration), separate from the §13 correctness-and-spend surface, and it carries no committed target until the MVP has produced real operating pain to size it against.

## Related pages

- [Invariants](method/invariants.md) — invariant #1 (family separation), the constraint the panel must not break.
- [Roles and models](method/roles-and-models.md) — the seat/tier assignment the panel extends to the review side.
- [Silent green](findings/silent-green.md) — "a run's own account of itself is not evidence", the principle behind the consensus guard.
- [The Phase 2 planning slice](overview/phase-2-planning-slice.md) — the reconciliation and decision-packet seats this phase compresses, and the calibration-divergence signal.

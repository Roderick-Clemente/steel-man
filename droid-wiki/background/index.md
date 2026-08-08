# Background

This repository is a specification plus a decision record. There is no application to read, so the reasoning behind the shape matters as much as the shape — why the design changed after Phase 0, why evidence sits where it does, and which questions are still open rather than quietly settled.

| Page | What it covers |
|---|---|
| [Design decisions](./design-decisions.md) | The choices that were made, with the evidence or reasoning behind each |
| [Open questions](./open-questions.md) | What is genuinely unresolved, plus the upstream defects Phase 0 found |
| [Operating rules](./operating-rules.md) | The 8 operating rules learned the hard way running this repo across agents and machines |

## Where the project came from

The method predates the repository. It has been run manually for months: one model plans, a model from a different family attacks the plan, both audit the test strategy, a cheap agent implements small chunks, and an independent agent validates each result. `README.md` is blunt about where the quality comes from — not a smarter model, but **structural separation of roles across model families**, with expensive thinking front-loaded into planning and executable evidence rather than self-assessment deciding whether work is done.

The canonical form of the sprint method itself — GROK → CHUNK → EXECUTE, TDD Red-Green-Refactor, independently executable chunk files, audit trail — is `templates/SPRINT-PLANNING-TEMPLATE.md`. Six-plus other repositories hold stale duplicates; that file is the one that counts. It is summarised in [Sprint template](../method/sprint-template.md).

## The problem being solved

PRD §2 lists the predictable failure modes of single-agent coding workflows and pairs each with the countermeasure the method applies: the author also grades the plan, the same agent writes the tests and the code, the reviewer inherits the author's framing, an import error gets called RED, review is advisory with no blocking contract, frontier models do mechanical work, and decisions live only in chat.

Then it names the actual product problem, which is narrower than "use two models":

> The most important product problem is not "use two models." It is **making independence and evidence structural properties of the run instead of prompt suggestions**.

PRD §3's goal follows from that: a reusable Factory plugin that takes an approved objective through planning, adversarial review, test design, chunked execution, independent validation, and a human-reviewable PR with a complete audit trail. The v1 non-goals are equally load-bearing — no rebuilding of Missions, Spec Mode, hooks, Droid Shield or CI, no auto-merge, no multi-repository work, no custom UI, and one pilot adapter rather than a general repo-ingestion engine.

## The three hypotheses

PRD §4 separates what must be *measured* from what must be *enforced*. The hypotheses are the measured half, and each is falsifiable:

| | Hypothesis | How it can fail |
|---|---|---|
| **H1** | Independent review finds material, non-overlapping issues — a reviewer from a different model family surfaces accepted correctness, scope, or test-strategy findings the planner missed | Cross-family review produces different noise rather than better findings. Measured as human-confirmed material findings unique to each reviewer, and as finding precision, so nitpicking is penalised |
| **H2** | Evidence gates reduce false completion — separating test design from implementation and verifying RED → GREEN mechanically catches claims that self-reporting misses | Counted as invalid-RED attempts caught and escaped defects |
| **H3** | Role-tiered models reduce cost without reducing task success — frontier planning and review plus cheaper execution costs less than an all-frontier run while preserving hidden acceptance-test results | **Conditional on Probe 7.** If usage cannot be attributed per role, H3 leaves the §13 evaluation and v1 makes no cost claim at all, because an unmeasured cost claim is worse than a missing one |

The enforced half is the eight [invariants](../method/invariants.md), and §13 is explicit that a demo looking good is not evidence for any of the three. "Models disagree at least once" is deliberately **not** a success gate, since it would reward manufactured findings. A clean null result counts as data.

The first observation bearing on H1 is now on the board — a hand-run pilot in which two cross-family reviewers each caught a different accepted defect the planner missed, and both independently caught a third. It is signal, not proof, and the run cannot separate family diversity from the different review lenses the two reviewers were given; see [First H1 observation](../findings/first-h1-evidence.md).

## Related

- [Overview](../overview/index.md) — current status and the one finding that matters most
- [Method](../method/index.md) · [Invariants](../method/invariants.md)
- [Probes](../probes/index.md) — the eight experiments that reshaped the design
- [Findings](../findings/index.md) — what Phase 0 concluded

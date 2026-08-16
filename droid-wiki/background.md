# Background

The design decisions in this project were shaped by one constraint above all: the platform cannot fail loudly. Phase 0 probes found four independent silent-green shapes — runs that do nothing, hooks that never load, models quietly downgraded, every tool call denied — all reporting exit 0. Every architectural choice downstream of that finding is a response to it. The full method is in [PRD.md](../PRD.md); the operating rules are in `tools/OPERATING-RULES.md`; the roadmap review that pressure-tested the arc is in `planning/ROADMAP-REVIEW.md`. For how the pieces fit together, see [overview](overview/index.md); for the method, see [the method](method.md); for the findings these decisions produced, see [findings](findings/index.md).

## Why command-orchestrated, not Mission-native

The PRD's §8 originally assumed Factory Missions as the orchestration substrate. `droid exec --mission` at 0.186.0 performs no work and reports success — zero turns, zero tokens, exit 0 (`evidence/phase-0/probe-1/`). That single defect blocked the mission-native path because per-role model flags (`--worker-model`, `--validator-model`) are only valid with `--mission`. The §8 contingency stood up: one `droid exec --model <id>` per role, with a wrapper owning the state machine. The `planning/phase-0/GO-NO-GO.md` decision is explicit — no to Mission-native, yes to command-orchestrated — and the redesign was required to land before Phase 2, not mid-Phase 3.

## Why the vendor adapter seam exists

Factory's envelope field names are not stable across versions. Probe 4 found that a guard keying on `file_path` saw `Execute`'s `command` instead, understood nothing, exited 0, and a locked file was overwritten. The adapter seam (`tools/adapters/README.md`) isolates vendor-specific shapes behind a single `NormalizedEnvelope` contract so that gates read normalised fields, not raw vendor output. Adding a new vendor means writing a new adapter module that returns the same shape. The seam is proven by hand on one vendor; the next vendor is out of scope until the contract is exercised against it.

## Why provenance is curated, not detected

PRD §4 states that model family provenance is maintained by hand in a curated map (`tools/sprint_loop/config.py:MODEL_FAMILY_MAP`), not inferred at runtime. Hosted providers will not declare an upstream base family, and nothing in the runtime can verify a claim of provenance. Any model absent from the map resolves to `unknown`, and `unknown` cannot satisfy a hard separation constraint — it stops the run. This is a known maintenance cost, accepted deliberately. A reviewer who declares a family inline that contradicts the curated map is refused at parse time; provenance by declaration is forbidden.

## Why the plan review is single-blind, not double-blind

PRD §5.3 makes the first reviewer pass single-blind: the reviewer sees the plan document and repository evidence, but not the planner's private reasoning and not a competing review. It is deliberately not double-blind. The reviewer reads the plan itself, so it inherits the plan's framing, vocabulary, and choice of what to make salient. Calling it "double-blind" would encourage the over-trust in independence that the method exists to avoid. Reconciliation may expose both positions, but agreement is only the absence of a known dispute — not evidence of correctness.

## Why max_review_rounds defaults to 2

The reconciliation loop is capped at `max_review_rounds`, defaulting to 2 revisions. This was challenged during cross-family review as too tight for legitimate scope disagreement. The PRD's response: it is a tuning parameter with a human escape hatch already attached, and it is the cheapest value in the document to change. The instruction is to set it from observed non-convergence rates, not from intuition before the first run. Phase 2's round 1 converged with zero blocking findings — a clean null result, valid per PRD §13.

## Why the three Droid definitions were kept

The PRD §8 revision notes that the plan reviewer, test designer, and validator Droid definitions were proposed for consolidation into "prompt variations." That was rejected: the roles carry different tool policies (plan reviewer read-only, test designer with test-file write, validator read-only plus execution) and different hard family constraints. Collapsing them collapses the invariants they exist to enforce. The principle: cut packaging, never role separation. The roadmap review reinforced this — the same-family test-author experiment in Phase 3.1 showed that collapsing a family constraint encodes test-independence bias directly into the output.

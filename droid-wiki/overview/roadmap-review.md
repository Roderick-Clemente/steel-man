# The roadmap review

**After six phases of building the adversarial sprint framework, a
roadmap review audited what was built, what was missed, and what the
sequencing should be next. The review itself went through two rounds of
cross-family panel review — the same process the framework preaches —
and was REJECTED on the first round for factual errors, then
APPROVE-WITH-NITS on the second. This is the story of that process and
what it produced.**

## Why the review was needed

The project had been building for six phases (0, 0.5, 1, 2, 3, 3.1, 3.2)
without a macro-level audit. Each phase had its own exit criteria and
review, but nobody had stepped back to ask: are we building the right
things in the right order? Have we been honest about what was actually
completed vs what was declared complete?

The review was prompted by the discovery of the orchestration gap during
Phase 3.2 — the process was ad hoc, run manually instead of by a scripted
pipeline. That gap was a framework-level concern, not a 3.2-specific one,
and it suggested there might be other gaps hiding in the phase history.

The review itself was recognized as **Phase 4 (Hardening + roadmap review)**
— a consolidation phase that arrived ahead of schedule. The cracks were
visible before the MVP was finished, and the roadmap review hardened the
foundation the same way Phase 6 (settling pass) was supposed to, just
earlier. All subsequent phases were renumbered: Phase 4 → Phase 5
(Generalize), Phase 5 → Phase 6 (Hardening settling pass), Phase 6 →
Phase 7 (Human compression).

## How the review was conducted

1. **Hydration:** The orchestrator (Factory Droid, Claude family) read all
   project documents — PRD, operating rules, telemetry schema, every phase
   directory's README/RESULTS/BUILD-NOTES/ASSUMPTIONS/KNOWN-ISSUES.
2. **Sub-agent audit:** One explorer sub-agent per phase (0 through 3.2),
   each answering: what was supposed to be built? what was actually built?
   what was missed?
3. **Synthesis:** The orchestrator combined all findings into a 5-section
   roadmap review: what's been done, what's next, missed wins, roadmap
   proposal, process improvements.
4. **Cross-family panel review:** The review was sent to Grok-4.5 and
   Gemini-3.1-pro-preview for independent audit — the same treatment every
   other artifact in the project gets.

## The v1 REJECT: the framework caught its own author

The v1 review was **REJECTED by both reviewers** for three material
factual errors:

1. **Phase 0.5 was declared "never built" — but it was DONE.**
   `tools/PHASE-0.5-CLOSE.md` marks it complete with all exit criteria
   checked. The review missed it entirely.

2. **The orchestration script was declared "never successfully ran" — but
   it did.** The review inspected 0-byte files in a dirty working tree
   and concluded failure. The committed telemetry told a different story:
   12 rows, 10 from orchestrated runs with real decisions. This was the
   exact failure mode the project's own OPERATING-RULES §7 warns about:
   "assert on reality, never on exit code." The review asserted on a dirty
   working directory instead of checking git history.

3. **Proposed rule §12 conflicted with PRD §13.** The rule said phases
   are incomplete until safety mechanisms are triggered. The PRD says "a
   clean null result is valid data" and manufactured disagreement is NOT
   a success gate.

The irony is the point: **a single-family review is not independence.**
The review was written by one model family (Claude) with zero cross-family
challenge. The project's entire thesis is that single-family review misses
things — and it did. The cross-family panel caught exactly the kind of
blind spot the framework exists to prevent.

## The v2 APPROVE-WITH-NITS: corrections accepted

The v2 incorporated all v1 panel findings: Phase 0.5 was acknowledged as
done, orchestration was correctly characterized as partially working, §12
was rewritten to match PRD §13, the signing key was closed as already
fixed, and the re-sequencing was adopted from the panel's recommendations.

Both reviewers returned **APPROVE-WITH-NITS**. The nits were improvements,
not corrections:

- **The Evidence Provider IS the KI-2 fix** (Gemini) — in bundle-consuming
  mode, validators don't need `Execute`, fully closing the write vector
  preventatively. But this must be parameterized so the H-CI control arm
  still works.
- **H3 was never scheduled** (Gemini) — H-CI measures review-side savings,
  but the primary cost hypothesis is H3 (can cheap executors actually
  implement without being handed the answer?).
- **Parallelize, don't serialize** (Grok) — three tracks not six buckets.
- **Act 3 overclaims** (Grok) — Droid Shield and OpenTelemetry were NOT
  Phase-0-verified. The review's own §16 rule says demo claims bind to
  verified capabilities, but the Act 3 list violated it.
- **§10 should be forward-looking only** (Grok) — don't retroactively void
  Phase 0.5/1 completions that used RUN-LEDGER.md as their system of record.

## The v3 final: Phase 4 — three parallel tracks

The v3 folds in all v2 nits. This review itself constitutes **Phase 4
(Hardening + roadmap review)** in the updated PRD §11 delivery plan — a
consolidation phase that arrived ahead of schedule because the foundation
needed attention before extending. The plan is three parallelizable tracks:

### Track A — Cheap closures (parallel, non-gating)

- Run `valid-red.py` against the existing locked test (closes the "never
  run" gap from Phase 1).
- Create 3-4 invalid-RED fixtures (closes the "invalid RED never
  demonstrated" gap).
- Package Act 1 from Phase 0.5 (the substance exists, just needs demo
  packaging).
- Reconstruct Phase 2 + Phase 3 telemetry rows from committed envelopes.

### Track B — Orchestration harden → H-CI → H3 (serial economic fork)

- Harden orchestration just enough for N identical runs (days, not a
  program): adapter shim, `run-with-model.sh`, stray-write baseline,
  transient retry, deterministic multi-run.
- Run the H-CI experiment: does the bundle save review-side tokens?
- Run an H3 validation: can a cheap executor actually implement without
  being handed the answer?

### Track C — Demo honesty (overlaps Track B after harden)

- Act 1 = package Phase 0.5 (done in Track A).
- Act 2 = command-orchestrated script, NOT Mission cosplay (the GO
  decision forbade Mission-native). Validators read bundles, no `Execute`
  tool = KI-2 fixed preventatively.
- Act 3 = ONLY Phase-0-verified controls (model pinning, hook enforcement,
  isolation guard, plugin scaffold). Droid Shield/OTel/air-gap = roadmap
  narrative until re-probed.
- "Close the laptop" = build a durable runner or drop the claim.

## What the process taught us

The roadmap review is itself a case study in the method working. A
single-family document had factual errors that changed its conclusion.
Cross-family review caught them. The corrected version is better — not
because the author was less intelligent, but because independence surfaces
blind spots that shared priors hide.

The new operating rule proposed by Gemini (§15: "assert on reality includes
git history") was aimed directly at the v1 failure: inspecting a dirty
working tree instead of the committed state. It is the project's own
epistemology applied to the project's own review. All 9 proposed rules
(§9–§17) have been landed in `tools/OPERATING-RULES.md` as part of Phase 4
closure.

## Phase 4 completion

Phase 4 is complete. All exit criteria met:

- **Orchestration stabilized** — adapter shim, stray-write baseline,
  transient retry, deterministic multi-run (Track B1).
- **H-CI results recorded** — 27.8% mean token saving (bundle vs
  in-session), quality holds (6/6 ACCEPT both arms), fairness rule holds
  (371 vs 1069 tokens, 65.3% saving on test-output slice).
- **H3 results recorded** — gpt-5.4-mini implemented from un-hinted spec,
  GREEN on first attempt, cross-family ACCEPT (Track B3).
- **Demo packaged** — Act 1 (manual baseline), Act 2 (command-orchestrated,
  no Mission cosplay, "close the laptop" dropped), Act 3 (Phase-0-verified
  controls only). Track C.
- **Telemetry SoR populated** — 34 rows in `runs.jsonl`, 71 findings in
  `findings.jsonl` from 9 review rounds.
- **Operating rules §9–§17 landed** in `tools/OPERATING-RULES.md`.

The track execution was itself cross-family reviewed. Grok returned REJECT
(7 findings, 2 HIGH: demo claimed Track B unfinished after it shipped,
telemetry not actually merged). Gemini returned APPROVE (0 findings). All
HIGH findings were fixed. The calibration divergence (Grok catches honesty
violations, Gemini gives clean passes) is now structured in `findings.jsonl`
for Phase 6 calibration.

## Artifacts

- `planning/ROADMAP-REVIEW.md` (v3) — the final review document
- `planning/REVIEW-PROMPT.md` — the cross-family panel review prompt
- `phase-3.2/reviews/roadmap-review-cross-family-findings.json` — v1 panel findings
- `phase-3.2/reviews/roadmap-review-v2-cross-family-findings.json` — v2 panel findings
- `phase-3.2/reviews/roadmap-review-{grok,gemini}-envelope.json` — v1 review envelopes
- `phase-3.2/reviews/roadmap-review-v2-gemini-envelope.json` — v2 gemini envelope
- `phase-3.2/reviews/roadmap-review-grok-envelope.json` — v2 grok envelope

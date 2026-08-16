# Phases

The project moves through numbered phases, each proving a specific claim or building a specific mechanism before the next one starts. Phase 0 was a feasibility spike; the arc runs through orchestration, hardening, a full loop runner, and a chunk-adherence enforcement layer. A parallel D-series refactor reorganized the repo's evidence and layout mid-arc. This page is a summary table; the phase descriptions live in `PRD.md` §6 and the planning directories linked below.

## Phase table

| Phase | Name | Status | What it proved / built | Key artifact |
|---|---|---|---|---|
| [0](../planning/phase-0/) | Feasibility spike | Complete | Model pinning, hook enforcement, isolation guard, per-role credit attribution probes. Established whether the invariants could be enforced at all. | `planning/phase-0/README.md` |
| [1](../planning/phase-1/) | Test-first execution | Complete | Valid RED → GREEN cycle with hash-locked tests. Proved that separating test authorship from execution catches false completion claims. | `planning/phase-1/` |
| [2](../planning/phase-2/) | Cross-family review | Complete | Different-family plan review with structured findings. Proved H1: independent review surfaces material, non-overlapping issues. | `planning/phase-2/` |
| [3](../planning/phase-3/) | Orchestration + telemetry | Complete | `orchestrate-review.py` pipeline and `telemetry/` system of record. Made review repeatable and runs measurable. | `planning/phase-3/` |
| [3.1](../planning/phase-3.1/) | Panel review | Complete | Cross-family panel on a planted defect. Proved the deterministic gate catches what aligned reviewers miss. | `planning/phase-3.1/` |
| [3.2](../planning/phase-3.2/) | Orchestrated REJECT/ACCEPT | Complete | Controlled rejection and acceptance drills. Proved the validator's blocking contract works under scripted conditions. | `planning/phase-3.2/` |
| [3.3](../planning/phase-3.3/) | Visual evidence tier | Seed only | Spike document exists; building waits on Phase 4 H-CI result. Not yet started. | `planning/phase-3.3/SPIKE.md` |
| [4](../planning/phase-4/) | Hardening + roadmap review | Complete | Roadmap audit, three parallel tracks (cheap closures, orchestration harden → H-CI → H3, demo honesty). Stabilized orchestration and recorded cost results. | `planning/ROADMAP-REVIEW.md` |
| [4.5](../planning/phase-4.5/) | Full loop runner + CI | In progress | `sprint-loop.py` coordinating all five roles from one command. Pluggable validation backend (local now, CI later). Turns the method from scripts into a product. | `planning/phase-4.5/` |
| [5](../planning/phase-5/) | Chunk-adherence enforcement | In progress | HMAC-signed chunk-completion tokens, `cross_family_review.py` refusal-at-parse, `chunk_sequence_gate.py`. Makes the §17.2 cross-family invariant structural rather than documented. | `planning/phase-5/` |
| [D1–D5A](../planning/layout-refactor/) | Layout + evidence refactor | In progress | Repo reorganization: D1 layout refactor, D2 orphaned evidence consolidation, D3 evidence hygiene, D4 final cleanup, D5 tooling-docs codification, D5A sweep-and-migrate (current branch). | `planning/evidence-hygiene/PLAN.md` |

## The arc

The early phases (0–3.2) proved the mechanism: independence controls work, evidence gates catch false completion, and the deterministic validator catches what aligned reviewers rationalize away. Each phase tested one hypothesis from `PRD.md` §4 against a live run rather than asserting it.

Phase 4 was an unscheduled consolidation. The foundation needed attention before extending — the roadmap review audited every prior phase through two rounds of cross-family panel review (v1 REJECT → v2 APPROVE-WITH-NITS → v3 final) and produced the operating rules now tracked in `tools/OPERATING-RULES.md`. Phase 4.5 turns the method into a product: one command fires the full sprint loop with retry on rejection and PR creation. Phase 5 makes chunk closure structural — a chunk is done when its HMAC-signed token verifies, not when the executor says so.

The D-series refactor ran in parallel with the phase work, reorganizing evidence layout and codifying tooling conventions so the repo could scale without the artifact structure becoming a liability. D5A (sweep-and-migrate) is the current active branch.

## Where to go next

- [Overview](overview/index.md) — what the framework is and what the runs found
- [The method](method.md) — the GROK, CHUNK, EXECUTE workflow and eight invariants
- [Findings](findings/index.md) — the headline discoveries from live runs
- [Features](features/index.md) — enforcement architecture and tooling

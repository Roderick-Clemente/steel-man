# Phase Guide

The adversarial-sprint-dev repository has been built in small, sequential phases. Each phase adds one piece of the framework and leaves committed evidence behind. This guide walks through them in order.

Phases 0 through 3 are complete and landed. Phase 3.3 is a seed only — the spec is written but the code is not built yet. Phase 0.5 is reserved in the numbering but does not have a directory or artifact yet.

| Phase | Name | Status | What it proved or built | Page |
|---|---|---|---|---|
| 0 | Feasibility spike | Complete | The platform can (and cannot) support cross-family, test-locked adversarial execution | [phase-0.md](phase-0.md) |
| 0.5 | Reserved | Not built | Gap in numbering; no artifact yet | — |
| 1 | Test-evidence vertical slice | Complete | A locked test can be authored, locked, validated as RED, and later verified GREEN without the executor touching it | [phase-1.md](phase-1.md) |
| 2 | Planning slice + cross-family plan review | Complete | A real plan for `/profile` was written, reviewed by two model families, and approved by a human bound to a hash | [phase-2.md](phase-2.md) |
| 3 | Execution sprint | Complete | The approved `/profile` plan was built in three chunks using the full adversarial loop | [phase-3.md](phase-3.md) |
| 3.1 | Degraded loop spike | Complete | Measured what happens when the test-author and executor share a model family | [phase-3-1.md](phase-3-1.md) |
| 3.2 | Evidence provider build | Complete | Local backend that produces a compact, signed evidence bundle so validators do not re-run pytest in-session | [phase-3-2.md](phase-3-2.md) |
| 3.3 | Visual / behavioral tier | Seed only | Spec for a screenshot/DOM evidence tier; not built yet | See `/Users/factory/work/adversarial-sprint-dev/phase-3.3/SPIKE.md` |

## The arc

- **Phase 0** asked whether the platform could even do this. The answer was "yes, but with guards we write ourselves." Factory Missions turned out to be a no-op at the tested CLI version, silent-green failures were common, and hooks had to be registered in the right file. The phase produced the design pivot: a command-orchestrated loop, not a native Mission.
- **Phase 1** took one lockable behavioral defect and showed the full test-evidence pipeline working: lock a test by SHA-256, confirm it fails RED for the right reason, run an executor that cannot edit the locked file, then verify it passes GREEN with the same hash.
- **Phase 2** added the planning half: a real plan for a read-only `GET /profile` page was drafted, reviewed by `grok-4.5` and `gemini-3.1-pro-preview`, reconciled, and approved by a human bound to a hash.
- **Phase 3** executed that plan in three chunks using the full loop: test-author → lock → valid-RED → cheap executor → cross-family validators. The openai executor seat was unavailable, so `glm-5.2` substituted with human approval.
- **Phase 3.1** deliberately degraded the loop: same cheap model family in both test-author and executor seats. The deterministic gate caught the bias every time; cross-family validation split 1-of-2; a retry fixed it. The structural lesson: cheap same-family authorship is only safe behind a standalone gate plus a fail-closed multi-model panel.
- **Phase 3.2** externalized the deterministic evidence tier: a local backend produces a signed `EvidenceBundle` with test results, locked-hash verification, and a security scan. Validators consume the bundle instead of re-running pytest in-session. The demo showed a 55% token saving on the test-output slice.
- **Phase 3.3** is the next tier: visual/behavioral evidence (screenshots, DOM assertions) against a running target. It inherits the same bundle abstraction but is intentionally not built until 3.2 is firm.

## Where to start reading

- If you want the platform evaluation: read [Phase 0](phase-0.md).
- If you want the test-locking machinery: read [Phase 1](phase-1.md).
- If you want the plan-approval story: read [Phase 2](phase-2.md).
- If you want the actual build of `/profile`: read [Phase 3](phase-3.md).
- If you want the cost/degradation experiment: read [Phase 3.1](phase-3-1.md).
- If you want the evidence-provider bundle: read [Phase 3.2](phase-3-2.md).

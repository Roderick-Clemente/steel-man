# Phase 2 — Planning Slice + Cross-Family Plan Review

Phase 2 added the planning half of the adversarial loop. The goal was to write a real plan for a bounded change, have it reviewed by two different model families, reconcile the findings, and get a human to approve it bound to a hash. Only then could execution begin in Phase 3.

The target was a read-only `GET /profile` page in the QuantumBank pilot, rendering the authenticated user's `username`, `email`, `full_name`, and a themed address for the demo identity Jean-Luc Picard.

## Key source files

| File | Purpose |
|---|---|
| `/Users/factory/work/adversarial-sprint-dev/phase-2/README.md` | Phase 2 brief, scope decisions, and panel composition |
| `/Users/factory/work/adversarial-sprint-dev/phase-2/plan-v1.md` | The approved plan, frozen at a SHA-256 hash |
| `/Users/factory/work/adversarial-sprint-dev/phase-2/APPROVAL.md` | Human plan-approval gate record |
| `/Users/factory/work/adversarial-sprint-dev/phase-2/findings.md` | Cross-family findings and amendments A1–A5 |
| `/Users/factory/work/adversarial-sprint-dev/phase-2/build-evidence/` | Planner and reviewer envelopes |
| `/Users/factory/work/adversarial-sprint-dev/phase-2/reviews/` | Review prompts |
| `/Users/factory/work/adversarial-sprint-dev/phase-2/KNOWN-ISSUES.md` | Operational findings during the slice |

## Scope decision

The phase began with a scope tension. The PRD defines Phase 2 as the adversarial planning slice, while a kickoff handoff suggested three other options (a second Werkzeug slice, reviewer calibration, or hook reachability). The brief decided to follow the PRD: the planning slice is on the critical path to Phase 3, and the other options belong in Phase 5.

## The plan

The planner seat was pinned to `claude-opus-5` (anthropic). The plan was written to `/Users/factory/work/adversarial-sprint-dev/phase-2/plan-v1.md` and hashed. It covered:

- Objective: authenticated, read-only `/profile` with no request parameter.
- Three chunks: a model getter in `/Users/factory/work/quantum-bank--llms-txt-pilot/models.py`, a route + template, and a demo seed identity.
- The `address` design fork: adding a nullable column, using a static config constant, or introducing a DAO layer. The plan chose option (b), a config constant with a migration TODO, because the pilot had no migration mechanism and the dev DB held a stale pre-Picard row.
- Acceptance criteria, risk table, and rollback strategy.

## Cross-family review

The review panel was `grok-4.5` (xAI) and `gemini-3.1-pro-preview` (google), both pinned. Reviewers were given fresh minimal context — only the plan, prior findings, and read-only repo state. No session reuse, no transcript sharing.

- `gemini-3.1-pro-preview` returned `APPROVE` with 0 findings.
- `grok-4.5` returned `APPROVE` with 3 medium and 3 low findings, all accepted as amendments A1–A5.

Both families approved with zero blocking/high findings, so the PRD Phase 2 exit criterion was satisfied. The plan was frozen at hash `sha256:72eccff5…`.

## Human approval

A human product owner approved the plan as-is on 2026-08-07. The approval bound execution to the exact plan hash. The non-blocking amendments A1–A5 traveled forward as binding acceptance criteria for the Phase 3 executor.

## Key lessons

- The planner must be read-only on the pilot repo and only get editor tools for writing the plan artifact in the framework repo. A first-round reviewer caught the planner being given too much write surface.
- Reviewers need `Execute` at `--auto high` to run verification binaries like `sqlite3`, even though they cannot edit files.
- A collision guard must fail closed on an `unknown` or unprovable family, not just swap on known collisions.
- `cache_read_tokens` should be logged so Phase 5 can measure the fresh-vs-reuse cost tradeoff.

## Relationship to Phase 3

Phase 2 produced the plan that Phase 3 executed. The plan hash bound the implementation, and amendments A1–A5 became the acceptance criteria for the `/profile` build.

# Phase 3.1 — RUN PROMPT (ready-to-run handoff)

You are the **orchestrator** for the Phase 3.1 spike: the budget-degraded loop.
Design rationale is in `phase-3.1/SPIKE.md` — read it first. This file is the
execution recipe. **You may run this now**; Phase 3 is complete and merged to
`main` (ade12c0) and is the control arm.

## The one variable under test

Everything is identical to the Phase 3 run **except the test-author seat**:

| Seat | Phase 3 (control) | Phase 3.1 (this run) |
|---|---|---|
| Test-author | `claude-opus-5` (anthropic) | **same cheap family as executor** (e.g. `glm-5.2`, zhipu) |
| Executor | `glm-5.2` (zhipu) | `glm-5.2` (zhipu) — unchanged |
| Validators | `grok-4.5` (xai) + `gemini-3.1-pro-preview` (google) | **unchanged, still pinned** |

This deliberately violates invariant #1 (test-author ≠ executor family) at the
test-author seat — that *is* the thing being measured: can the pinned
cross-family validators catch the same-family biases the lost test-independence
would otherwise let through? **Do not** relax the validator pinning; the whole
experiment is whether frontier cross-family *validation alone* compensates.

## Guardrails (experiment validity + repo safety)

1. **One variable only.** Change *only* the test-author family. Same plan
   (plan-v1, `sha256:72eccff5…`), same 3-chunk structure, same accepted
   assertions, same lock/valid-RED/GREEN/validate cycle, same reasoning efforts.
   Do **not** also change the evidence source — that is Phase 3.2's variable.
2. **Isolate the pilot working tree.** A Phase 3.2 planner (and possibly other
   agents) may be active. Run against an isolated checkout so you never share a
   working tree:
   ```
   git -C /Users/factory/work/quantum-bank--llms-txt-pilot worktree add \
     ../qb-phase-3.1 8a10711d
   ```
   Work in `../qb-phase-3.1` on a branch `factory/phase-3.1-degraded`.
3. **Never trust a run's own account.** Re-verify every GREEN against the
   hash-locked test gate (`phase-1/scripts/verify-green.py`) and run a
   `git status` stray-write check after every validator run (KI-2).
4. **Stop at the human gate.** Present results; do not self-merge.

## Steps

1. Hydrate: `phase-3.1/SPIKE.md`, `phase-3/README.md`, `phase-3/RUN-COMMANDS.md`
   (swap the test-author model), `phase-3/KNOWN-ISSUES.md`, the Phase 3 wiki
   entry, `telemetry/SCHEMA.md`, and the Phase 3 rows in `telemetry/runs.jsonl`
   (the control numbers).
2. Confirm the Phase 3 baseline is reproducible (pilot suite green at the base).
3. Set up the isolated worktree (above).
4. Run the full loop for all 3 chunks with the degraded test-author seat. Reuse
   the Phase 3 prompts in `phase-3/prompts/` verbatim where possible — the
   point is that *only the model seat* differs.
5. Capture every envelope to `phase-3.1/build-evidence/`. Preserve failures.
6. Emit telemetry rows tagged `phase-3.1` (extend `phase-3/gen-telemetry.py`;
   reuse its parsing so numbers come from envelopes, not transcription).

## Deliverables (the evidence, not intuition)

Compare against the Phase 3 control and answer, with numbers:
- Did the same-family tests encode biases the validators caught? Which ones?
- Did validator findings differ in **count / severity / category** vs Phase 3
  (which had 0 findings)?
- Did the final code pass the **same acceptance criteria** (locked tests +
  full suite)?
- **Token cost delta** vs the 541k Phase 3 baseline, per seat.

Write it up in `phase-3.1/RESULTS.md` and update `phase-3.1/SPIKE.md`'s "What
the results would tell us" with the observed outcome. Feed the honest result
(graceful-degradation path **or** hard floor for invariant #1) to the §13
efficacy surface and Phase 5 calibration.

## Definition of done

All 3 chunks run under the degraded seat; results written; telemetry rows
emitted; presented for the human gate. No self-merge, no second variable
introduced.

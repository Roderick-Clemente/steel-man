# Recommendation — sequencing 3.1 / 3.2 / 3.3 and first lens to prototype

Planner output. **Stop for human review before any building.**

## Sequencing (updated: 3.1 has now completed)

**3.1-DONE → 3.2 (build local → experiment → then Harness) → 3.3 (next evidence tier).**

Plus one non-gating follow-on: **wiki-refresh** rides on 3.2's trigger infra and
can land opportunistically any time after 3.2 — it is a small operational chore,
not a phase, and does **not** sit beside or block 3.3.

- **3.1 is COMPLETE** (`phase-3.1/RESULTS.md`; ran on an isolated worktree,
  presented at the human gate, not merged). Result was *panel-dependent*, not a
  clean pass/fail: a same-family author weakened 1 of 3 chunks' tests, `grok-4.5`
  caught it, `gemini-3.1-pro-preview` did not. Load-bearing lesson carried into
  3.2/3.3: the deterministic gate + a **≥2-model fail-closed panel** are what
  compensated — a single model is not a safe gate. It also produced the new
  **PRD §17.6** (degrading the test-author family invariant is an outage
  fallback, not a cost lever).
- **3.2 builds the local backend first**, and H-CI runs with **zero CI** before
  Harness is involved (isolates "structured evidence" from "the vendor").
- **3.2 experiment, then Harness backend** to prove the interface is
  interchangeable. Guardrail from the EXPLORER-PROMPT still holds: **one variable
  per run** (never combine degraded-models with CI-evidence), and isolate the
  pilot tree with `git worktree` if any other experiment runs concurrently.
- **3.3 after 3.2** lands the abstraction (3.3 extends the same interface;
  building it first would fork the interface).

## First lens to prototype

**The local evidence backend + validators consuming the bundle (3.2 build steps
1–3), run as H-CI before touching Harness.** Rationale:

1. It isolates the real variable — *"panel reads a compact structured bundle
   instead of raw pytest stdout"* — from *"Harness is involved,"* so a positive or
   null H-CI result is attributable to externalization itself, not to a vendor.
2. It honors the zero-CI-default principle and needs no MCP/CI infra to produce
   first evidence.
3. It reuses `phase-1/scripts/verify-green.py` for the locked-hash cross-check,
   so the §4.1 trust rule is satisfied on day one.

Harness backend (build step 4) comes second, only to prove the interface is
interchangeable — not to generate the first H-CI datapoint.

## What the Phase-3 baseline already predicts

H-CI's realized win is bounded by the size of the in-session **test-output read**
(the only part CI removes); diff-read and verdict-reasoning do not move. The
context-heavy validator (`gemini`, 96k–165k input/run) holds most of the
headroom; `grok` (16k–30k input) holds little. So predict a **partial** win, and
the phase-3 slice's own suspicion — that panel size and validator context
discipline are the bigger lever — may well be reconfirmed. That is a valid null
result (PRD §13), and the spike is instrumented (fairness rule §3.2) to say which.

## Open questions that need a human decision

1. **Framework-repo trigger timing** — ship the outbound git trigger for the
   framework repo with 3.2, or rely on quantum-bank's existing trigger for the
   H-CI run? (The pilot trigger is sufficient to run the experiment.) See the
   dogfood target, `phase-3.2/SPIKE.md` §7.
2. **Executor MCP grant** — default is *no* (hidden tests must stay out of its
   context). Confirm it stays no for the pilot, or define the exact
   own-change-only scope if ever granted.
3. **Local scanner choice** — Semgrep, Bandit, or both for the local security
   lens? (Interface-agnostic; affects only the coverage-lens report, not H-CI
   cost.) Note the §4.4 lessons: whichever is chosen must gate on **new-vs-baseline**
   and carry a **curated allowlist** (the gitleaks/`SPLIT_CLIENT_KEY` false-fail).
4. **SCHEMA bump coupling** — KI-4 (`role` enum missing `test-designer`) and the
   need to record MCP call/payload tokens for the §3.2 fairness rule both point at
   a `telemetry/SCHEMA.md` `schema_version` bump. Do it once, before the 3.2
   experiment, so treatment-arm rows can carry the MCP-token fields.
5. **3.3 target-env policy** — fresh-seeded vs dev-like persistent target (the R3
   surface); recommendation is *both, reported separately*, but it is a human call
   (see `phase-3.3/SPIKE.md` §5).
6. **Wiki-refresh (a CI-triggered agent task) sequences AFTER 3.2, not as a
   separate track.** It is downstream work that *reuses* 3.2's CI trigger +
   run-an-agent-from-the-pipe machinery (§7 CI-as-runner / flavor a); it should
   not be planned or built in parallel as its own thing. Of its sub-decisions:
   **cadence is clear** — on-merge, not every commit (cost + churn +
   non-deterministic output settle it). **The review gate is the one open
   decision left**: auto-generated narrative still needs an author≠approver gate
   before landing on `main` (no auto-merge), but gating every refresh on a human
   may be too heavy — that trade-off is unresolved and worth more thought. A
   `phase-3.2/wiki-refresh-on-merge.md` draft is already in flight on another
   agent's wiki branch; reconcile the review-gate decision there once 3.2 lands.

## Deliverables produced this pass (refreshed)

- `phase-3.2/SPIKE.md` — evidence-provider abstraction (interface + local default
  + Harness backend + §2.3 two backend flavors + §2.4 auto-resolving selection),
  H-CI design (metric, mandatory fairness rule, confound controls), trust rules
  (locked-sha account, §4.2 chunk-boundary gate + fail-closed, §4.3
  augment-not-replace with 3.1 corroboration, §4.4 security-gate discipline from
  the first Harness run), MCP seat allocation, §7 dogfood + agent-task scope.
- `phase-3.3/SPIKE.md` — visual/behavioral tier seed (R3 motivation, extended
  bundle, surface options, visual-validator independence with the 3.1
  single-judge corroboration).
- this recommendation.

No pipeline code, no MCP wiring, no pilot edits. Awaiting human review.

# Beyond Phase 3 — Explorer / Planner handoff (3.2 + 3.3)

You are a **planner**, not an executor. Your mandate: turn the decisions below
into concrete, reviewable specs and a recommendation, then **stop for human
approval before any building**. This mirrors the framework's own rule —
planner ≠ executor, plan before build. Do not write pipeline code, MCP wiring,
or pilot changes in this pass; produce specs.

## Where things stand

Phase 3 is complete and merged to `main` (ade12c0): the full plan→execute→review
loop proven on the pilot `GET /profile` slice, 3 chunks, 6/6 cross-family
ACCEPT, pilot suite 99 passed. Baseline telemetry is in `telemetry/runs.jsonl`
(**541k tokens total, validators ~84%, executor ~13%, test-designer ~3%**). The
pilot feature branch `feat/user-profile` is pushed to the public quantum-bank
remote. Phase 3.1 (budget-degraded loop) has its own ready-to-run handoff at
`phase-3.1/RUN-PROMPT.md` and may be running in parallel with your planning.

## The theme you are speccing

**Externalize the deterministic evidence tier out of the model sessions and into
CI, with the model panel consuming it.** Today the executor and *each* validator
re-run pytest in-session and read raw output — a big part of the 84% validator
cost. The idea: a neutral evidence producer (CI) runs the deterministic work and
the agents consume a compact, structured result.

Human decisions from the originating session (carry these forward — do not
relitigate unless you find a real problem):

- **Split the work:** **3.2 = tests + security externalized to CI**;
  **3.3 = visual/behavioral (screenshot/DOM) validation**. Spec both; 3.2 is
  the near-term one.
- **No vendor lock-in — CI is a *mode*, not a dependency.** Define an abstract
  **evidence-provider** interface. Default backend = **local** (pytest +
  `phase-1/scripts/verify-green.py` hash check + a local scanner such as
  Semgrep/Bandit) so the loop runs with **zero CI**. Harness is *one* backend;
  other CIs stub in later. The method depends on the capability, never Harness.
- **Integration edges are native, no bespoke connector:**
  - *Outbound (invocation):* git trigger on push/merge fires the pipeline (one
    already exists on quantum-bank; one for the framework repo is planned).
  - *Inbound (evidence):* **Harness MCP** — a Factory agent *pulls* structured
    results (tests, coverage, SARIF, Test-Intelligence) on demand, rather than
    scraping artifacts.
- **MCP seat allocation (default):** validators **yes** (the 84%, primary win);
  orchestrator **yes** (gating + locked-hash cross-check); executor/"coder"
  **default no** — the deciding constraint is that hidden tests must stay out of
  *every* agent's context (executor included); if ever granted, scope to its
  *own* change's results only. All MCP access **read-only**, scoped to *this
  change's* results, never whole-org visibility.

## The headline experiment 3.2 must be built to prove

**Hypothesis (H-CI):** routing deterministic evidence through CI *reduces average
token cost at equal acceptance quality.* Phase 3 is the control arm; 3.2 is the
treatment arm (same locked slice, same validator families, same acceptance
gate — the only changed variable is the evidence source).

Design it to be *credible*, not a vibe:

1. **Metric:** total input+output tokens to reach the same ACCEPT, per chunk and
   summed; paired with acceptance-pass-rate (must **not** drop — cheaper-but-worse
   is not a win, per PRD §13).
2. **Fairness rule (mandatory):** count the **MCP call + returned payload
   tokens** on the treatment side. Offloading is not free; the win is real only
   if the structured evidence bundle is smaller than the in-session test output
   it replaces. Predict a **partial** win — the validator still pays to read the
   diff, and that cost does not move.
3. **Keep security scans OUT of the token comparison.** They *add* a lens (new
   findings) — a coverage gain, not a cost delta. Report separately so "did CI
   make it cheaper" stays clean.
4. **Control confounds:** identical models, reasoning efforts, prompts, and diff;
   only the evidence source differs. Run N times (single runs lie).

## Trust rules to preserve (do not let CI weaken the method)

- **"CI says green" is itself an account.** The pipeline must publish the
  **locked-test sha it actually ran**; the orchestrator cross-checks it against
  the local lock manifest. Trust "CI ran the *locked* test (hash matches) and it
  passed," never a bare green.
- **Pre-merge vs on-merge:** the *gate* pipeline runs on the feature branch
  (pre-merge) so validators have evidence before the human merge gate; the
  on-merge-to-main pipeline is the regression/security baseline.
- **CI augments, does not replace, the model panel.** Tests + scans are
  necessary-not-sufficient; the cross-family review of the diff (spec/semantics/
  over-exposure) still stands.

## Real evidence from the first Harness run (design these in)

The pilot's `feat/user-profile` was run through the Harness pipeline. It
produced three concrete lessons that the 3.2 spec must account for — all from
findings that were **pre-existing debt, not introduced by the Phase 3 change**:

- **Gate on NEW findings vs a baseline, not total history.** Gitleaks failed the
  build on `fail_on_severity: low` against the full 89-commit history, yet its
  own report said `newIssuesCount: 0` — the finding was legacy debt, not new in
  this change. If the gate keys on total history, every run trips on old debt
  and the "did *this change* introduce a problem?" signal drowns. The gate must
  diff against a baseline (SARIF `newIssues*` / new-occurrences) and use a
  proportionate `fail_on_severity`.
- **The scanner is not an oracle — a human/model still classifies findings.**
  Gitleaks flagged `SPLIT_CLIENT_KEY` (a Split.io *client-side* key that is
  public by design — it ships in browser JS) as `generic-api-key` on a pure
  entropy heuristic. False positive. This is the "an account is not evidence"
  rule applied to CI: the security tier needs a **curated allowlist** (scoped to
  the specific known-public value, not whole files, so real future secrets still
  trip) and its verdicts feed judgment, they don't end it.
- **Diff-scoped vs history-scoped scanning are both valid at their scope.** The
  orchestrator's pre-push scan was diff-scoped (our new commits — correctly
  found nothing); gitleaks was full-history (found legacy debt). The 3.2 design
  should be explicit about which scope gates the merge (diff/new) vs which is a
  standing baseline report (history).

## 3.3 seed (spec lightly, don't build)

Motivating evidence already in hand: during Phase 3 the live `/profile` rendered
**"Demo User"** against the persistent dev DB even though the seed change was
correct — a fresh-DB unit test hid what a visual/behavioral lens would have
caught (the R3 stale-DB caveat). That is the case for a screenshot/DOM tier.
Surfaces to weigh: Harness hosted Playwright + screenshot agent, Factory Droid
Control / Automated QA, local Playwright. A visual **validator is still a
validator** — it occupies a seat and must respect family separation (≠ executor,
cross-family with the panel). Name whose model powers any screenshot-judging
agent, and fold it into the independence accounting.

## Parallelization guidance

3.1 and 3.2 are independent variables against the same Phase-3 control, so they
parallelize — with two guardrails: (1) **one variable per run** (never combine
degraded-models with CI-evidence), and (2) **isolate the pilot working tree**
(`git worktree`) when both are running experiments. Your *planning* pass is
read-only and safe to run alongside a live 3.1 run.

## Deliverables

1. `phase-3.2/SPIKE.md` — the evidence-provider abstraction (interface +
   local-default + Harness backend), the H-CI experiment design (metric,
   fairness rule, confound controls), trust rules, and the pre-merge wiring.
2. `phase-3.3/SPIKE.md` — the visual/behavioral tier seed, surface options, and
   the independence treatment of a visual validator.
3. A short **recommendation**: sequencing (the session's lean is 3.1-now /
   3.2-plan-in-parallel / 3.2-experiment-after-CI-and-MCP), the first lens to
   prototype, and any open questions that need a human decision.

Then **stop for human review**. No pipeline code, no MCP wiring, no pilot edits
in this pass.

## Hydration pointers

`PRD.md` §13 (efficacy eval) and §17.1 (seat pinning / when `--auto` is allowed);
`telemetry/SCHEMA.md` + Phase 3 rows in `telemetry/runs.jsonl` (control numbers);
`droid-wiki/overview/phase-3-execution-slice.md` (the cost finding);
`phase-3/KNOWN-ISSUES.md` (KI-1..4); `phase-3.1/SPIKE.md` (the adjacent spike and
the per-seat fallback-registry note).

# Phase 2 brief — cross-family review prompt (round 1)

You are a **cross-family reviewer** on the Adversarial Sprint project. You are
reviewing a **brief** (a planning document), not code. Your job is to decide
whether the Phase 2 brief is sound enough to authorize the vertical slice it
describes, and to surface any material problem before a single paid planner or
reviewer call is spent.

## Your tooling

You have `--enabled-tools Read,Glob,Grep,LS,Execute`. `Execute` is enabled
**deliberately** so you can run read-only shell-outs — `git show`, `git log`,
`cat`, `pytest --collect-only`, etc. — to check claims against the actual
repository. Use it. (In Phase 1 a reviewer refused to render judgment because
`Execute` was missing; that will not happen here. If you still feel blocked,
say exactly what command you needed.)

Do **not** modify any file. This is a read-only review.

## What to read

1. **The brief under review:** `phase-2/README.md` on branch
   `factory/phase-2-slice`.
2. **The authority it must conform to:** `PRD.md` — especially §5.2-5.3 (GROK +
   single-blind review + reconciliation), §6 (oversight + decision packets),
   §9 (artifacts), §11 (phase definitions, incl. Phase 5 scope), §13
   (evaluation), §17 (model discipline).
3. **Repo conventions:** `AGENTS.md`, `tools/conventions/commit-body-recipe.md`,
   `telemetry/SCHEMA.md`.
4. **Prior art it builds on:** `phase-1/README.md`,
   `droid-wiki/overview/meta-narrative.md`, `phase-1/build-evidence/*.json`.
5. **The pilot target:** `~/work/quantum-bank--llms-txt-pilot` — the `/profile`
   objective in §2.5. Verify the schema claims (`models.py` users table has no
   `address` column and no password field; no existing `/profile` route).

## The decision you must return

Return exactly one verdict: **ACCEPT**, **ACCEPT-WITH-NITS**, or **REJECT**.

- **ACCEPT / ACCEPT-WITH-NITS** authorizes the slice to proceed. Nits are
  recorded but do not block.
- **REJECT** blocks the slice and forces another brief round. Reserve it for a
  material defect: a spec deviation, an unsound exit criterion, a missing
  invariant, or an objective that cannot carry the phase.

## Specific questions to adjudicate (answer each explicitly)

1. **D3 (load-bearing) — scope.** §0 decides Phase 2 = the PRD §11 "adversarial
   planning slice", and leaves reviewer-calibration in Phase 5 (where §11 filed
   it near-verbatim). Is this the right call, or must calibration precede
   planning? If you reject §0, the whole brief re-scopes — so be explicit.
2. **D1 — objective.** Is the read-only `/profile` page (§2.5) genuinely
   bounded (2-4 chunks, one service), and does it carry at least one real
   error/boundary path per PRD §10? Is leaving the `address` schema fork to the
   planner (rather than pre-deciding it) appropriate, or a cop-out?
3. **D5 — model policy.** §7 refines PRD §17.1 to allow `--auto` at the
   **planner** seat (with recorded attribution + a family-collision guard) while
   keeping **reviewers pinned**. Is the attribution-vs-enforcement distinction
   sound? Is the collision guard sufficient to guarantee cross-family
   separation before the run? Note this depends on a §17.1 amendment landing on
   `main` via a convention branch.
4. **Exit criteria (§4).** Are they correct and complete? In particular: is
   "APPROVE-bound-to-hash OR correctly-escalated decision packet" a legitimate
   dual exit, and is the clean-null-result framing consistent with PRD §13?
5. **Failure classes (§5).** Does the brief anticipate the real failure modes?
   Anything missing (e.g., the Phase-1 `Execute`-missing tooling blocker is
   F-plan-4 — is that mitigation adequate)?
6. **Conventions.** Do the planned commit-body trailers (§8) and telemetry row
   shapes (§8) conform to `commit-body-recipe.md` and `telemetry/SCHEMA.md`?
   Is the "telemetry rows stay gitignored" handling (§8, PRD §17.3/§17.4)
   correct?
7. **D2 / D4** — fresh-reviewer-always + Phase-5 deferral of the reuse knob;
   and `max_review_rounds` = 2. Reasonable?

## Output format

```
VERDICT: ACCEPT | ACCEPT-WITH-NITS | REJECT

D1: <read> ...
D2: <read> ...
D3: <read> ...
D4: <read> ...
D5: <read> ...

FINDINGS (each: severity blocking|major|minor|nit, surface = README section,
claim, evidence incl. any command you ran, recommended change):
- ...

SUMMARY: <2-4 sentences: what would you change before code, if anything>
```

Ground every material finding in evidence — a section pointer, a PRD clause, or
a command you actually ran. A finding without evidence is a nit at most.

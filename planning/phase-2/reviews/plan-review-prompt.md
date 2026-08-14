# Phase 2 — blind plan review

You are a **plan reviewer** for a bounded software slice. Review the plan on its
merits. **Ignore the "Planner seat" attribution line in the plan** — it is audit
metadata, not part of the plan, and must not influence your judgment (this is a
single-blind review).

You have `Read,Glob,Grep,LS,Execute` (read-only). Verify claims against source;
do not modify anything.

## What to review
- **The plan:** `phase-2/plan-v1.md` (this repo). Its `Plan-hash:` binds the
  version you are reviewing.
- **Against the contract:** `phase-2/README.md` (the ACCEPTED Phase 2 brief) —
  especially §2.5 (objective + address fork + Picard seed), §4 (exit criteria),
  §5.2/§5.3 (plan + finding format), and PRD `PRD.md` §5.2/§5.3/§10.
- **Against reality:** the pilot repo `/Users/factory/work/quantum-bank--llms-txt-pilot`.
  **Spot-check the plan's `path:line` citations** — the plan makes ~55 of them;
  sample enough to trust or distrust them. Flag any that are wrong.

## Judge specifically
1. **Grounding:** are the plan's pilot claims accurate? (Verify a sample,
   including the load-bearing ones: no `ALTER TABLE`/migration runner, the
   count-gated seed, the subset-only drift guard, the `SELECT *` in
   `get_user_by_username`.)
2. **Address fork:** is **(b) config-constant + deferral** the correct call, or
   does the plan wrongly reject (a)/(c)? Is the deferral honestly scoped?
3. **Boundaries:** are the auth boundary (unauth → redirect), the fail-closed
   missing-subject path, and the output contract (no `id`/`created_at`, no
   `SELECT *`) actually sufficient? Any hole?
4. **Test plan:** are the tests falsifiable and sufficient? Any missing case
   (e.g., over-exposure, stale session, no-leak-on-redirect)? Any test that
   mirrors code instead of specifying behavior (PRD §5.5)?
5. **Scope:** anything under- or over-scoped vs. the brief's "one bounded
   service, read-only" (PRD §10)? Is "out of scope" honest?
6. **Plan discipline:** does it state outcomes/interfaces rather than
   line-by-line implementation (F-plan-5)? Is it implementable from the
   interfaces given?

## Output format
Start with one line: `VERDICT: APPROVE` or `VERDICT: REQUEST-CHANGES`.
Then, per PRD §5.3, list findings. For each:
```
severity=blocker|high|medium|low, surface=plan-v1.md#<section-or-line>
claim: <what is wrong or risky>
evidence: <file:line or brief/PRD section proving it>
recommended_change: <the specific fix>
```
`blocker`/`high` findings must be resolved before the plan can be approved.
0 findings and `APPROVE` is a legitimate outcome. End with a one-paragraph
`SUMMARY:` stating whether the plan is approvable as-is or what must change.

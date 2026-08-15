# Evidence — pilot AI-discovery run (`llms.txt` family)

The artifacts behind [First H1 observation](../../droid-wiki/findings/first-h1-evidence.md).
This directory is the primary record; the findings page is the reading of it.

**Scope.** A hand-run pilot, not a plugin run. The pilot target is
[QuantumBank](https://github.com/Roderick-Clemente/quantum-bank) — a small Flask demo bank
already named across `PRD.md`, `README.md`, and the pilot spec in `tools/`. Four bounded
units added machine-readable surface (`/llms.txt`, `/llms-full.txt`, `/robots.txt`,
`/sitemap.xml`). One frontier model planned and orchestrated; two cross-family models
(Grok, Kimi) validated in fresh contexts. This is the **adversarial arm** — it is not the
Phase 0.5 baseline (same change done a second way for comparison), which was not run.

**Environment.** Executor: `droid` 0.180.0 on the build host. Validators: Grok and Kimi in
fresh sessions. Orchestrator/planner: Claude Opus 4.8. Dates 2026-08-03 / 2026-08-04.

## The units

| Unit | Surface | Merged as | Merge commit |
|---|---|---|---|
| 1 | `/llms.txt` (short manifest) | direct to main | `308aaa70` fix + `8a10711d` lock |
| 2–3 | `/robots.txt`, `/llms-full.txt` (+ Kimi cleanup) | [PR #9](https://github.com/Roderick-Clemente/quantum-bank/pull/9) | `a1050a87` |
| 4 | `/sitemap.xml` (closes dangling ref) | [PR #10](https://github.com/Roderick-Clemente/quantum-bank/pull/10) | `f37d6ada` |

All four are live on qbank.dev.

## The findings, as evidence

Three validator outputs are captured under [`validator-outputs/`](./validator-outputs/). Grok's review is verbatim; the Kimi record is reconstructed from commit messages and the executor's report, and is labelled as such in the file; the Unit 4 close-out is verbatim:

| File | Reviewer / lens | Material finding | Overlap? |
|---|---|---|---|
| [`kimi-nits-and-charset.md`](./validator-outputs/kimi-nits-and-charset.md) | Kimi, content | Process-narrative leaked into the served manifest (Unit 3 FIX 1) | Unique to Kimi |
| [`grok-ai-discovery-review.md`](./validator-outputs/grok-ai-discovery-review.md) | Grok, abuse | `robots.txt`/`llms-full.txt` promised a `/sitemap.xml` that 404'd | Unique to Grok |
| both, on Unit 1 | Grok **and** Kimi | Doubled `charset` in `/llms.txt` `Content-Type` (RFC-malformed) | **Overlapping — both families, blind** |
| [`sitemap-unit4-validation.md`](./validator-outputs/sitemap-unit4-validation.md) | Unit 4 close-out | dangling `/sitemap.xml` now resolves 200 | — |

The doubled-charset catch is the honest counterweight to the non-overlap story: two
independent families converged on the same real defect. Commit `308aaa70`'s message records
it directly — *"Both Grok and Kimi flagged the same shape in their post-build reviews."* Both
reviewers graded it a "nit," which is precisely what H1's precision metric is built to weigh.

## What this evidence does and does not support

- **Supports:** independent cross-family review surfaced material findings the planner and
  executor missed — one unique to each reviewer, plus one both caught. The RED→GREEN and
  true-removal lock proofs are in the outputs (assert-on-reality, not exit code).
- **Does not support any cost claim.** The two reviewers were given *different lenses*
  (content vs. abuse), so family-independence and lens-diversity are confounded. No
  same-prompt A/B was run. H3 is untouched.
- **N = 4 units, one pilot, one operator, one sitting.** Enough to show the mechanism fires;
  not enough for a rate, a precision figure, or an effect size.
- **The plugin did not do this.** Isolation and model separation were held by operator
  convention, not by the reference guard or a router. This is the manual arm the plugin will
  later be measured against.

## Provenance note

The validator outputs are transcribed from the run's own session records. Local worktree
paths (an internal machine detail) were redacted; no finding text was altered. The mini's
`quantum-bank-findings.md` is a secondary synthesis and is deliberately **not** the basis
here — these are the primary reviewer outputs and the committed QuantumBank history.

# First H1 observation — a pilot run

Executor `droid` **0.180.0**; validators Grok and Kimi in fresh sessions; orchestration Claude Opus 4.8. Run 2026-08-03 / 2026-08-04. Evidence in `planning/pilots/ai-discovery/`.

Every other page in [Findings](./index.md) is scoped to Phase 0, and Phase 0 was explicit about its ceiling: it answered whether the platform **can** enforce the invariants, not whether the method **works**. That second question is the [H1/H2/H3 evaluation](../background/index.md#the-three-hypotheses) in PRD §13, and it belongs to a later phase.

This page is the first datapoint from that later phase. It is **not** a Phase 0 conclusion and does not change the [GO/NO-GO](./index.md#the-verdict). It records the method run by hand against a live pilot — the **adversarial arm**, not the [Phase 0.5 baseline](../background/open-questions.md#product-decisions-still-open) (which would run the same change a second way for comparison, and was not run) — so there is at least one real observation on the board before the plugin exists to produce many.

Read it as **signal, not proof.** Four units, one pilot, one operator, one sitting. What it establishes is that the H1 mechanism produced its predicted effect at all; it does not bound how often, how large, or at what cost.

## What was run

The pilot target is QuantumBank, a small Flask demo bank already named across `PRD.md`, `README.md`, and the pilot spec in `tools/`. Four bounded units added machine-readable surface to the site — a short AI manifest, an expanded manifest, a `robots.txt`, and a sitemap. Each unit ran plan → implementation of a single reviewable chunk → validation, and ended in a human-reviewed merge to `main` (Unit 1 direct; Units 2–3 via PR #9; Unit 4 via PR #10; merge commits tabulated in the evidence README).

One model planned and orchestrated. Two models from different families, Grok and Kimi, validated. The validators ran in **fresh contexts** and never saw the executor's reasoning, build log, or completion report — the isolation invariant [#2](../method/invariants.md) protects, enforced here by convention rather than a guard, because there is no plugin yet. The Grok review carries an explicit isolation attestation naming the files it did not read; the other two outputs do not attest it in their own text. Captures in `planning/pilots/ai-discovery/validator-outputs/`.

## The finding

**Each of two independent cross-family reviewers surfaced an accepted defect the planner and executor missed, and the two defects did not overlap — and on a third defect, both reviewers converged.**

| Reviewer | Lens it was given | What it caught | Overlap |
|---|---|---|---|
| Kimi | Content / correctness of the served text | The expanded manifest leaked internal process narrative into a machine artifact | Unique to Kimi |
| Grok | Abuse / can this be pointed at something wrong | `robots.txt` promised a sitemap URL that returned 404 — a dangling reference | Unique to Grok |
| **Grok and Kimi, blind** | (their own, on Unit 1) | Doubled `charset` in the `/llms.txt` `Content-Type` — an RFC-malformed header | **Both families caught it** |

All three were accepted and each changed the artifact. None was graded blocking: Grok's verdict on Units 2–3 was **ACCEPT-WITH-NITS**, filing the dangling sitemap under *"Nits (non-blocking)"*; both charset commits call that fix a *"nit"*; Kimi's content findings were logged as nits. So the run produced **three accepted, non-blocking findings** — real defects that shipped fixes, not correctness breaks. Whether that clears H1's bar for *material* is what the precision metric exists to settle, and it is not computed here.

The unique two are the non-overlap H1 predicts — a second reviewer surfaced a finding the first did not. The third is the honest counterweight: both families independently flagged the same doubled-charset header (recorded in QuantumBank commit `308aaa70`: *"Both Grok and Kimi flagged the same shape in their post-build reviews"*). That convergence is evidence the review produces **signal, not noise** — H1's failure mode is "different noise rather than better findings," and two families landing on the same real defect is the opposite of noise.

Everything else, both reviewers accepted — the [clean null result that counts as data](../background/index.md), not a failure to find fault.

## The lens-diversity confound

The two reviewers were given **different lenses** — one read the content for correctness, the other probed for misuse. That is the likeliest reason their unique findings did not overlap, and it is why this run cannot answer the question underneath H1 and [H3](../background/index.md#the-three-hypotheses): does a second model add value because it is independent, or because it was pointed somewhere new?

The run never held the lens constant while varying the model, so family-diversity and lens-diversity are confounded. The doubled-charset convergence cuts both ways. It is evidence the review produces signal rather than noise, since two families independently landed on the same real defect. But it is not evidence for non-overlapping *value* — on that finding the second reviewer was redundant, which is the cost case against a second seat. It does not resolve the lens confound either, since a defect both lenses caught may simply have been the easy one.

A clean test, **same prompt and same artifact to two cross-family models**, was not run. Until it is, the run says nothing about cheap-versus-frontier cost, and H3's [cost claim stays out of the evaluation](../background/open-questions.md#probe-7-usage-attribution-is-only-partially-unblocked), exactly as PRD §13 requires when the measurement is confounded.

## The operator produced a false green

While building the regression proof for one fix, the operator first mutated the asserted string into a **superstring** of itself — replacing a word with a longer word that still contained it — so the substring assertion passed for the wrong reason and proved nothing. It was caught and redone as a true removal, at which point the test failed correctly. The Grok review ran the same true-removal discipline and named the trap in its own output (*"Trap demo: 'fictional' → 'fictionalX' still contains fictional"*); the Unit 4 validation ran an equivalent inject-and-restore cycle.

It is recorded because it is the same class of false-green the method exists to prevent ([Silent green](./silent-green.md)), and it appeared on the *orchestration* side, not the executor's — a small argument for the [force-the-bypass house rule](../how-to-contribute/patterns-and-conventions.md): a control not actively made to fail is measuring manners.

## What this page does not claim

- **Not a Phase 0 finding.** Phase 0 is closed and this does not reopen it. This is early post-Phase-0 evidence living in Findings only because it is the first reading of the H1 mechanism in operation.
- **N is four.** Four units, one pilot, one operator, one sitting. Enough to show the mechanism *can* fire, not to estimate a rate, a precision figure, or an effect size. [H1's precision metric](../background/index.md#the-three-hypotheses) is not computed here.
- **No cost claim.** The lenses were not held constant, so cheap-versus-frontier is [confounded](#the-lens-diversity-confound) and H3 is untouched.
- **The plugin did not do this.** Isolation was held by convention, not by the [reference guard](./reference-guard.md); model separation was operator-enforced, not routed. This is the manual arm the plugin will later be measured *against*, and an arm that works by hand does not prove the automated version will.

## Related

- `planning/pilots/ai-discovery/` — the primary artifacts this page reads
- [Background — the three hypotheses](../background/index.md#the-three-hypotheses) — what H1 predicts and how it is measured
- [Findings](./index.md) — the Phase 0 conclusions this sits after, not among
- [Open questions](../background/open-questions.md) — the Phase 0.5 baseline and the confounds this run leaves open
- [Silent green](./silent-green.md) · [Patterns and conventions](../how-to-contribute/patterns-and-conventions.md) — the false-green discipline the operator defect illustrates

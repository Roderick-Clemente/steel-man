# planning/evidence-hygiene/PLAN.md

Process codification lineage for `planning/evidence-hygiene/` chunks.
chunk-D3-1 and chunk-D4-1 review verdicts cite "per
`planning/evidence-hygiene/PLAN.md §5`" — but §5 did not yet exist as a
tracked file when those chunks landed. chunk-D5 authors this PLAN to
close the citation gap. Two sections; D5 is one chunk, not a
multi-chunk programme.

## 1. Source of truth for the process tiers

`tools/sprint_loop/config.py:MODEL_FAMILY_MAP` is the canonical
model-family taxonomy. `tools/cross_family_review.py` enforces the
gate. `tools/orchestrate-review.py` is the cross-family reviewer
pipeline. `tools/run-with-model.sh` is the per-invocation refusal
layer. Reviewer-firing **tier selection** is defined in §2.

## 2. Review tier spectrum

| Tier               | Trigger                                                                                              | Reviewers                | Token    | Cost       | Precedent                                                                          |
|--------------------|------------------------------------------------------------------------------------------------------|--------------------------|----------|------------|------------------------------------------------------------------------------------|
| `audit-script-only`| Spec is "run these N scripts and report whether they pass"; no judgement calls                     | 1 (any family)           | none     | ~5-8 min   | `chunk-D4-1` @ `0663444` (single round, dual cross-family ACCEPT-WITH-NITS)         |
| `judgment-call`    | Spec involves an exclusion-set decision, label, reframing, or any choice with two defensible answers | 2 (cross-family)         | optional | ~15 min    | `chunk-D3-1` @ `58c11d3` (round-2 fix; round-1 REJECT was at `685e379`)            |
| `spec-level`       | Spec itself changes (dossier edit, sweep-rule, taxonomy change)                                     | full panel (≥2 families) | required | ~30 min    | `chunk-D1-*` / `chunk-D2-1` @ `42aa9ca` (referee tokens issued)                    |

Verify any tier's example via `git show <sha>`. §2 is the load-bearing
content for `planning/evidence-hygiene/` chunks going forward.

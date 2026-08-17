# Branch triage — 2026-08-16

One-line disposition per unmerged branch, recorded for Rod to confirm Monday.
Nothing was merged or deleted on this pass. Method: `git cherry` patch-equivalence
against `origin/main` (933f532), main-reflog merge records, and content presence
checks in main's tree. Dispositions verified by hand where the automated pass
flagged uncertainty.

## Needs a decision (not merged, real content)

| branch | ahead | disposition | evidence |
|---|---|---|---|
| `factory/readme-ci-onboarding-fixes` | 1 | READY — held for Monday (merge = publish) | README pilots/ path + Python 3.10 floor; verified clean 2026-08-16 |
| `factory/readme-accuracy` | 1 | LIVE — overlaps the branch above | same README region (test counts, pilots/ path, 3.10 note); reconcile the two before merging either. Was LOCAL-ONLY until late 2026-08-16 (working-rule-1 violation, caught in cross-review when Max could not see it on origin); pushed since |
| `fix/chunk13-shallow-clone-skip` | 0 | ALREADY ON MAIN — safe to delete | `git cherry` = patch-equivalent; skip logic present at `tests/test_sign_chunk_token.py:195-201` |
| `agent/referee/phase-5-chunkadherence` | 1 | PARTIALLY MERGED — do not delete | c0ba01c (token signing) patch-equivalent on main; e813e12 (referee review summary, verdict matrix for 5a-5e) is NOT on main and the file exists nowhere in main's tree — unmerged evidence |
| `factory/chunk-14-kn-J-fixes` | 1 | LIVE (deliberately paused) | PHASE-5-LAUNCH-PROMPTS.md cites 623e024 as the phase-4.5 resume point; J-7 BLK + J-8/9/10/11/15/16 still open |
| `factory/chunk-e-contract-reader` | 1 | LIVE (deliberately paused) | backlog-E contract reader; cited by SHA 9c069e0 in PHASE-5-LAUNCH-PROMPTS.md; no contract reader on main |

## Merged or superseded (content verified on main; candidates for deletion)

All patch-equivalent, reflog-recorded merges, or content regenerated on main:

`factory/d5-tooling-docs`, `factory/d5-tooling-docs-1b`, `factory/layout-refactor`,
`factory/d3-evidence-hygiene`, `factory/d2-evidence-consolidation`,
`factory/d4-final-cleanup`, `factory/phase-5-chunkadherence-enforcement`,
`factory/canary-0.180-bugs`, `factory/readiness-fixes`, `factory/readme-front-door`,
`factory/family-vocab`, `factory/plan-lint`, `factory/recheck-wiring`,
`factory/review-attestation-gate-spec`, `factory/secops-sprint`,
`factory/d5a-sweep-and-migrate`, `pr-5`, `claude/ops-docs`,
`factory/convention-model-discipline-v2`, `factory/phase-1-hardening`,
`factory/phase-2-slice`, `factory/phase-3.1`, `factory/phase-3.2-evidence`,
`factory/phase-3.2-spec`, `factory/phase-4-track-a`, `factory/wiki-phase-3-ci`,
`factory/wiki-phase-3.1`.

Notes:
- `factory/wiki-phase-3-ci` / `factory/wiki-phase-3.1`: their wiki pages were
  regenerated wholesale by PR #11; the branch content is superseded, not merged.
- `factory/canary-0.180-bugs`: landed via the tagged `pre-canary-merge` /
  `canary-0.180.0-*` merge; the plan's "likely abandoned" guess was wrong — it merged.
- The 2026-08-16 fix branches (`factory/ki4-finding-parser`,
  `factory/ki3-empty-stage-commit`, `factory/ki5-rewrite-spec-layer`) are new
  tonight and out of scope for this triage.

## Corrections to the Sunday-plan inventory

- Plan said "seven branches, ~16 commits"; the true surface was ~32 branches, of
  which 27 were already merged/superseded. Real unmerged work: 6 branches above.
- `fix/chunk13-shallow-clone-skip` was listed "probably ready"; it is already on
  main in patch-equivalent form and needs no merge.
- `factory/layout-refactor` "superseded?" — confirmed merged (D1 complete).
- `factory/d3-evidence-hygiene` "4 ahead, triage" — confirmed merged.
- `factory/canary-0.180-bugs` "likely abandoned" — confirmed merged.

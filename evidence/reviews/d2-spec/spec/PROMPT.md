# Cross-family spec review: chunk-D2-1 (consolidate orphaned build evidence)

You are an independent Tier-2 reviewer. Adversarial, evidence-first.
Do not defer to the builder, the planner, or to any earlier review.

## What to review

Repo: `/Users/factory/work/adversarial-sprint-dev`
Branch: `factory/d2-evidence-consolidation`
Spec under review: `planning/evidence-consolidation/CHUNK-D2-1-SPEC.md`
  (sha256 bc963befb0b82610f12c03594332ce880b7672c0900b8a18be85d18d2cfa84e6)
Parent plan: `planning/evidence-consolidation/PLAN.md`
  (sha256 f5ac16a6..., reviewed and accepted at plan gate)

## Context

D1 established the `evidence/phase-N/` taxonomy but left a top-level
`build-evidence/` outlier (34 tracked files, ~1.4MB). D2-1 consolidates
location without changing any evidence byte. All moves are `git mv` only.
6 files are duplicates of a canonical D1 run tree and must be quarantined
to `legacy-duplicates/` to avoid overwriting the canonical tree.

## Your job — challenge these, in order

1. **Are the 34 files correctly identified?** Verify the count: `git ls-tree -r
   --name-only HEAD -- build-evidence/ | wc -l`. Check that 28 files have no
   destination collision under `evidence/phase-4.5/build-evidence/` and that
   the 6 duplicate files under `build-evidence/r-drs-role-split-1/` are
   correctly identified as duplicates of the canonical
   `evidence/phase-4.5/build-evidence/r-drs-role-split-1/` tree.

2. **Is the quarantine approach sound?** The 6 duplicate files move to
   `evidence/phase-4.5/build-evidence/legacy-duplicates/r-drs-role-split-1/`
   instead of overwriting the canonical tree. Verify that the canonical tree
   exists and that the quarantine path does not collide with any existing path.
   Is `legacy-duplicates/` the right isolation, or could a reviewer confuse
   quarantined files with canonical ones?

3. **Is the judge design sound?** §3.3 requires a judge that is side-effect
   free, asserts real state, and is not vacuous. The inventory must be a
   committed artifact, not generated at assertion time from the post-move tree.
   Is this design sufficient? Can you construct a partial implementation that
   passes the judge while leaving a defect? For each of the 6 judge assertions,
   verify it tests the property, not a proxy.

4. **Are the exit criteria measurable and complete?** §4 lists 8 exit criteria.
   Can each be objectively verified? Is anything missing — for example, should
   there be a check that no file under `build-evidence/` remains after the move?
   Should the SHA-256 manifest be committed as evidence rather than just
   produced?

5. **Are the forbidden actions properly fenced?** §5 lists 7 forbidden actions.
   Is anything missing? Should there be a fence against touching
   `tools/phase-1-locks/` (the lock manifests)? Against touching any judge file
   from D1?

6. **Is the spec consistent with the plan and D1 precedent?** The plan was
   reviewed and accepted. Does this spec implement what the plan promised? Does
   it follow D1 conventions (git mv only, no byte edits, append-only LEDGER,
   separate locked judge file, etc.)?

7. **Scope and capacity.** Is 34 files / 1 chunk within the §17 capacity
   envelope? Is the one-commit requirement achievable? Could the quarantine
   step introduce a scope escape?

8. **Token and sequence gate.** §1 references `chunk-D1-4.token.json` as the
   predecessor. Verify this token exists and is signed. The spec says the
   builder does not sign — is this consistent with §22?

## Rules

- Cite `file:line` or `spec §` for every finding.
- Verify claims yourself. The spec and this prompt may both be wrong.
- Distinguish severity: `blocker`, `high`, `medium`, `low`, `nit`.
- If something is genuinely correct, say so briefly.

## Required output

Findings as a list, each with:
```
- severity: blocker|high|medium|low|nit
  category: correctness|spec-deviation|silent-green|factual|sequencing
  section: <file:line or spec §>
  claim: <what the spec asserts or does>
  evidence: <what you found>
  recommended_change: <specific>
```

End with exactly one line:

`VERDICT: ACCEPT` or `VERDICT: ACCEPT-WITH-NITS` or `VERDICT: REJECT`

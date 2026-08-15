# Cross-family plan review: D2 evidence consolidation PLAN

You are an independent Tier-2 reviewer. Adversarial, evidence-first.
Do not defer to the builder, the planner, or to any earlier review.

## What to review

Repo: `/Users/factory/work/adversarial-sprint-dev`
Branch: `factory/d2-evidence-consolidation`
Artifact under review: `planning/evidence-consolidation/PLAN.md`
  (sha256 `f5ac16a6c407d137bf788137ba3e97d12fcb36f3e0082bed9becc36f49b37451`,
  commit `581bdd1`)

This is a **plan review**, not a code review. The chunk has not been built yet.
You are reviewing whether the plan is sound, scoped, and fence-compliant before
the builder writes a CHUNK-SPEC and code.

D1 moved phase-N silos into `evidence/phase-N/`. D2 consolidates the remaining
34 orphaned files (1,410,544 bytes) under the top-level `build-evidence/` into
the existing `evidence/phase-4.5/build-evidence/` taxonomy.

## What the PLAN claims

1. **Scope**: 34 files, 1,410,544 bytes. 28 non-duplicate files move to
   `evidence/phase-4.5/build-evidence/`. 6 `r-drs-role-split-1/` files are
   logical duplicates of an already-canonical D1 run record; they go to
   `evidence/phase-4.5/build-evidence/legacy-duplicates/` as a location-only
   quarantine.

2. **Method**: `git mv` only. No evidence file contents change. An exact-content
   comparison found 41 duplicate groups; the plan explicitly does NOT delete
   any of them — hash equality is evidence for measurement, not permission.

3. **Fences**: Do not touch `evidence/phase-N/` taxonomy, `evidence/phase-4.5/tokens/`,
   signing keys, `main`, runtime path constants, wiki prose, or review protocol
   semantics.

4. **Exit criteria**: SHA-256 manifest before/after; `git diff --numstat` shows
   zero content delta; `git log --follow` reaches pre-D1 history for three
   representative files; full suite green; plan-lint PASS; wiki-link-audit PASS;
   no token created or modified.

5. **Capacity**: One chunk, one commit, one bounded source root. A failure after
   one bounded correction is STOP/BLOCKED, not scope expansion.

## What to check

1. **Scope measurement**: Are the 34 files and 1,410,544 bytes real? Run your own
   `find build-evidence -type f | wc -l` and `du -sb build-evidence` against this
   commit. Is the duplicate classification correct — do the six
   `r-drs-role-split-1` files actually duplicate the canonical D1 copy?

2. **Fence integrity**: Does the plan's allowed surface (git mv only, no evidence
   byte edits) cover everything the chunk needs? Does it fence everything it
   shouldn't touch (tokens, constants, wiki, phase-N taxonomy)?

3. **Exit criteria completeness**: Are the five exit checks sufficient to catch a
   defective build? Is anything missing — residual paths, stale references,
   judge coverage?

4. **D1 precedent**: Does this plan respect the D1 architecture (per-chunk judges,
   locked tests, immutable evidence bytes per §21, builder doesn't touch locked
   judges per invariant #3)?

5. **Risk**: What is the worst plausible failure mode if this plan is executed
   as written? Are there silent-green risks (checks that pass while wrong)?

## Rules

- Cite `file:line` or `§` for every finding.
- Severity: `blocker` (plan cannot proceed), `high`, `medium`, `low`, `nit`.
- If the plan is sound, say so briefly and specifically. Do not pad.

## Required output

```
- severity: blocker|high|medium|low|nit
  category: scope|fence|exit-criteria|precedent|risk|factual
  section: <PLAN.md § or line>
  claim: <what the plan asserts>
  evidence: <what you found, file:line, measured counts>
  recommended_change: <specific>
```

End with exactly one line:

`VERDICT: ACCEPT` or `VERDICT: ACCEPT-WITH-NITS` or `VERDICT: REJECT`

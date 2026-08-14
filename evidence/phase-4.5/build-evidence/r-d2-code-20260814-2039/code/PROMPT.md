# Cross-family code review: chunk-D2-1 (consolidate orphaned build evidence)

You are an independent Tier-2 reviewer. Adversarial, evidence-first.
Do not defer to the builder, the planner, or to any earlier review.

## What to review

Repo: `/Users/factory/work/adversarial-sprint-dev`
Branch: `factory/d2-evidence-consolidation`
Build commit under review: **42aa9ca**
Spec: `planning/evidence-consolidation/CHUNK-D2-1-SPEC.md`
D2 judge: `tests/test_evidence_consolidation_d2.py`
Diff of the build: `build.diff` in this directory.

Suite interpreter: `/private/tmp/asprint-venv/bin/python` (3.13.3). If unavailable,
build your own venv and report the path and version. Do NOT report counts from
3.9.6 — it has no pytest.

This chunk consolidates 34 orphaned build-evidence files from the top-level
`build-evidence/` directory into `evidence/phase-4.5/build-evidence/` using
`git mv` only. 6 duplicate files are quarantined to
`evidence/phase-4.5/build-evidence/legacy-duplicates/r-drs-role-split-1/`.
No evidence byte is changed.

## Your job — challenge these, in order

1. **Are all 34 files moved with zero content change?** Run
   `git show --numstat --format= -M 42aa9ca` and verify every evidence file
   shows 0/0 (rename, no content edit). Flag any file with additions or
   deletions.

2. **Is `build-evidence/` gone?** Verify no top-level `build-evidence/`
   directory exists. Check `git ls-tree HEAD -- build-evidence/` returns
   empty.

3. **Are the 6 duplicate files correctly quarantined?** Verify the 6 files
   under `legacy-duplicates/r-drs-role-split-1/` exist and that the canonical
   `evidence/phase-4.5/build-evidence/r-drs-role-split-1/` tree is untouched.
   Compare the quarantine files against the canonical tree — are they true
   duplicates?

4. **Is the SHA-256 manifest correct?** The spec requires a pre/post
   SHA-256 manifest proving all 34 bytes unchanged. Find it in the evidence
   bundle and verify: every source file's hash matches its destination file's
   hash.

5. **Is the D2 judge sound?** Read `tests/test_evidence_consolidation_d2.py`.
   Does it assert real state (file existence, SHA-256 match, no top-level
   build-evidence/) rather than proxies? Can you construct a partial
   implementation that passes the judge while leaving a defect?

6. **Are all D1 judges byte-unchanged?** Hash all 5 D1 judge files and compare
   to lock manifests under `tools/phase-1-locks/tests/`. The D2 build must not
   touch any D1 judge.

7. **Is the suite green?** Run the full suite. Expected 241 passed, 3 skipped.
   Report counts and interpreter path.

8. **Scope escapes.** Confirm: no token files created or modified, no
   `config.py` changes, no `PATH-REDIRECTS.md` changes, no wiki content
   changes, no force-push, no `main` branch touched.

9. **Exit criteria from §4.** Verify each of the 8 exit criteria from the spec
   is met: pytest green, plan-lint green, wiki-link-audit green, git diff
   shows 34 R100 relocations with 0 content changes, git log --follow reaches
   pre-move history for representative files, SHA-256 manifest proves bytes
   unchanged, D1 constants/tokens unchanged, one commit with correct subject.

10. **D2 completeness.** Is the orphaned evidence fully consolidated? Is
    anything left behind that should have moved?

## Rules

- Cite `file:line` for every finding. No finding without evidence.
- Verify claims yourself.
- Distinguish severity: `blocker`, `high`, `medium`, `low`, `nit`.
- Do not commit, stage, or modify anything.

## Required output

Findings as a list, each with:
```
- severity: blocker|high|medium|low|nit
  category: correctness|spec-deviation|silent-green|factual|sequencing
  section: <file:line or spec §>
  claim: <what the artifact asserts or does>
  evidence: <what you found>
  recommended_change: <specific>
```

End with exactly one line:

`VERDICT: ACCEPT` or `VERDICT: ACCEPT-WITH-NITS` or `VERDICT: REJECT`

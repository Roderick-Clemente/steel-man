# Cross-family code review: chunk-D1-3 (living-doc citations, PATH-REDIRECTS, LEDGER rename)

You are an independent Tier-2 reviewer. Adversarial, evidence-first.
Do not defer to the builder, the planner, or to any earlier review.

## What to review

Repo: `/Users/factory/work/adversarial-sprint-dev`
Branch: `factory/layout-refactor`
Build commit under review: **<BUILD_COMMIT>**
Spec: `planning/layout-refactor/CHUNK-3-SPEC.md`
Chunk-3 judge: `tests/test_layout_paths_chunk3.py`
  (sha256 `5c66bcfc1b42c6fe1d07376ee899f4fd9d98f4909acce761710f3bd3e1ad3362`,
  locked at `tools/phase-1-locks/tests/test_layout_paths_chunk3.py.lock.json`)
Chunk-1 judge: `tests/test_layout_paths.py` (sha256 `cb00dfac…`, skips post-flip)
Chunk-2 judge: `tests/test_layout_paths_chunk2.py` (sha256 `48a579f8…`)
Chunk-2a judge: `tests/test_layout_paths_chunk2a.py` (sha256 `7289ca09…`)
Diff of the build: `build.diff` in this directory.

Suite interpreter: `/private/tmp/asprint-venv/bin/python` (3.13.3). **This is not
`/usr/bin/python3`**, which is 3.9.6 and has no pytest installed. If the venv
path does not exist on your machine, build your own and report the path and
version. Do NOT report counts from 3.9.6 — it has no pytest.

chunk-D1-2 moved 618 tracked files out of the `phase-N/` silos. chunk-D1-3
updates living-doc citations to the new homes, creates
`planning/PATH-REDIRECTS.md` to carry the 683 tokens that must not be edited
(evidence bytes, historical narrative, locked-judge comments), and renames
`planning/phase-4.5/LEDGER.md` to `evidence/LEDGER.md` as a pure `git mv`.

The builder filed 13 findings (F1–F13). F13 (BLOCKED on the rename assertion)
was resolved by the planner at a later commit — the judge's `git show --numstat`
used a pathspec that broke rename detection. The fix drops the pathspec and
filters the output for the LEDGER line.

## Your job — challenge these, in order

1. **Are the citation rewrites correct and complete?** The builder claims 57
   mechanical rewrites across 13 files, leaving 49 residuals in 2 narrative
   files (`droid-wiki/by-the-numbers.md` and `droid-wiki/lore.md`), all
   enumerated in `planning/PATH-REDIRECTS.md`. Verify: run the judge's own
   `_residual_tokens()` scan, check that every surviving residual is listed in
   PATH-REDIRECTS, and that no rewritten citation now points at a path that
   does not exist. A re-rooted citation to a nonexistent file is the §7
   silent-green shape — looks swept, isn't.

2. **Are the 4 dead relative links actually fixed?** The builder claims 4 dead
   markdown link targets in README.md were fixed (the matcher's lookbehind
   excludes `](./phase-N/…)` targets). Verify: resolve every relative link in
   the §2.1a surface files against the filesystem. Zero dead. The builder's
   F3 notes the matcher blind spot — check whether any new dead link was
   introduced by the rewrites.

3. **Is PATH-REDIRECTS.md correct and non-vacuous?** The builder's
   `gen-path-redirects.py` derives the 44-row prefix table from `ee90061`'s own
   rename records and refuses to emit a row whose destination does not resolve
   on disk. Verify: every `old → new` row in the table, the new prefix
   resolves. Every residual token in the §2.1a surface is either rewritten or
   enumerated as an exception. The generator's refusal mechanism (F6) means the
   judge's "every residual is accounted for" is not satisfied by construction —
   confirm this by checking that the narrative exceptions are hand-classified,
   not auto-generated.

4. **Is the LEDGER rename a pure rename?** The builder claims `git mv` with
   +0/-0. Verify with `git show --name-status --find-renames <BUILD_COMMIT> --
   evidence/LEDGER.md`: it should show `R100` (byte-identical). Also confirm
   `planning/phase-4.5/LEDGER.md` no longer exists and `evidence/LEDGER.md`
   does. The LEDGER rows appended by the builder in a later commit (9014db6)
   are separate from the rename commit — confirm the rename commit itself
   carries no content edit to the LEDGER.

5. **Are all four judges byte-unchanged?** Hash each judge file and compare to
   the lock manifests under `tools/phase-1-locks/tests/`. The builder may not
   modify the test that judges it (invariant 3). The chunk-3 judge was amended
   by the planner (pathspec fix at a later commit) and re-locked by the
   referee — confirm the on-disk hash matches the lock.

6. **Is the suite green at the right counts?** Run
   `/private/tmp/asprint-venv/bin/python -m pytest -q` (or your own venv if
   that path does not exist). Expected **234 passed, 3 skipped**. The 3 skipped
   are Chunk-1 judge tests that skip post-flip. Report the counts you observe
   and the interpreter path you used.

7. **§5 hard stop: are the 683 unedited tokens actually unedited?** The builder
   claims 683 tokens across `planning/layout-refactor/**`, `planning/phase-N/**`,
   and committed evidence are deliberately unedited. Verify:
   `test_chunk3_redirect_only_surfaces_untouched` passes. Check that the build
   diff touches no file under `evidence/phase-4.5/build-evidence/` (evidence
   bytes are immutable). The one exception is the LEDGER rename itself.

8. **Scope escapes.** This chunk edits citations and creates PATH-REDIRECTS.md.
   Any `R` status line in `git show <BUILD_COMMIT> --name-status` other than
   the LEDGER rename is out of scope. Confirm nothing was written under
   `evidence/phase-4.5/tokens/` (the builder does not hold the signing key,
   §22). Confirm the `.cursor/rules/*.mdc` changes are generated mirrors of
   allowlisted SKILL.md files (builder F7) and not hand-edits.

9. **Audit the spec and findings for further issues.** The builder filed 13
   findings. Check each one: are F1 (by-the-numbers is a measurement) and F2
   (lore.md is a build record) correctly classified as narrative exceptions?
   Is F4 (OPERATING-RULES stale tails) a legitimate scope widening or an
   out-of-scope edit? Is F9 (SoR pollution affecting chunk-2a judge) a real
   risk for future runs? Are there findings the builder should have filed but
   did not?

10. **Chunk-4 safety.** Does anything in this build make the next chunk harder
    or unsafe? The LEDGER is now at `evidence/LEDGER.md` — does any code or
    test still reference the old path in a way that would break? The
    `test_layout_paths.py:571` comment citing the old LEDGER path is
    lock-frozen (builder F8) and covered by PATH-REDIRECTS — confirm this
    build did not touch it.

## Rules

- Cite `file:line` for every finding. No finding without evidence.
- If you assert a site is missed or a path changes, SHOW the before and
  after strings.
- Verify claims yourself. The spec and this prompt may both be wrong.
- Distinguish severity honestly: `blocker` (chunk cannot close),
  `high`, `medium`, `low`, `nit`.
- If something is genuinely correct, say so briefly and specifically.
- Note the Python interpreter path and version in your report.
- Do not commit, stage, or modify anything. You are read-only
  plus `Execute`; a review that mutates the artifact under review is void.

## Required output

Findings as a list, each with:
```
- severity: blocker|high|medium|low|nit
  category: correctness|spec-deviation|silent-green|factual|sequencing
  section: <file:line or spec §>
  claim: <what the artifact asserts or does>
  evidence: <what you found, with file:line and strings>
  recommended_change: <specific>
```

End with exactly one line:

`VERDICT: ACCEPT` or `VERDICT: ACCEPT-WITH-NITS` or `VERDICT: REJECT`

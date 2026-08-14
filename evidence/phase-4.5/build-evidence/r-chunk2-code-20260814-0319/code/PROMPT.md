# Cross-family code review: chunk-D1-2 (git mv phase dirs + flip constants)

You are an independent Tier-2 reviewer. Adversarial, evidence-first.
Do not defer to the builder, the planner, or to any earlier review.

## What to review

Repo: `/Users/factory/work/adversarial-sprint-dev`
Branch: `factory/layout-refactor`
Build commit under review: **ee90061**
Spec: `planning/layout-refactor/CHUNK-2-SPEC.md`
Chunk-1 judge: `tests/test_layout_paths.py` (sha256 cb00dfac…, skips post-flip)
Chunk-2 judge: `tests/test_layout_paths_chunk2.py` (sha256 48a579f8…, runs post-flip)
Diff of the build: `build.diff` in this directory (non-rename changes only;
618 file renames at R100 are summarized in FINDINGS-chunk-D1-2.md).

Chunk 2 moves every tracked file from `phase-N/` silo dirs to taxonomy
homes (`evidence/`, `planning/`, `tools/phase-N-*`), flips the seven
layout constants to the new roots (VALUE-only, relative segments
preserved), updates the layout allowlist, linters, CI workflow, and
test fixtures. Evidence bytes are immutable — git mv preserves bytes.

## Your job — challenge these, in order

1. **Did every git mv preserve bytes?** The builder claims 618/618 R100
   (0 insertions, 0 deletions). Verify: `git show ee90061 --summary |
   grep -v R100` should show no non-rename operations. Pick files from
   each destination class and confirm history follows via
   `git log --follow`.

2. **Are the flipped constants correct per §2.2?** Each must be an
   independent relative segment — no `framework_root` reference, no
   cross-constant coupling (e.g. `os.path.join(EVIDENCE_ROOT, ...)`).
   Verify against the spec's 7 value rows. Check that `BUILD_EVIDENCE_REL`
   is unchanged and `BUILD_EVIDENCE_DIR` auto-flipped via `EVIDENCE_ROOT`.

3. **Are the 6 findings reasonable?** The builder documented 6 items
   beyond §2.1–§2.4 in `FINDINGS-chunk-D1-2.md`. For each:
   - Is the judgment call correct?
   - Does it introduce a defect or close one?
   - Should any have been raised as BLOCKED instead?

   Pay special attention to:
   - **Finding 2 (.gitignore refusal):** The builder refused §2.3's
     instruction to add `evidence/*/build-evidence/r-*/`, arguing it
     reinstates a silent-loss shape that previously destroyed signed
     referee token envelopes. Is the refusal correct? Is the technical
     claim about directory-form excludes accurate?
   - **Finding 1 (destination shape):** The builder chose leaf-preserving
     (per PLAN §4 Rule) except for leaves named `evidence` absorbed by
     the root. Three independent pins agree. Is this the only consistent
     reading?

4. **Were any sites missed?** Run your own grep for live `phase-[0-9]`
   path construction under `tools/`, `evidence/`, `planning/`, `.github/`.
   The Chunk-2 judge scans 9 routed files with a strengthened matcher
   (12 idioms, 0 false positives). But the matcher does NOT scan test
   files or fixtures. The builder reports 2 split-segment sites in test
   files that the suite caught but the judge couldn't. Are there more?

5. **Do both judges work as designed?** Chunk-1 judge should SKIP (3/3)
   because `EVIDENCE_ROOT != ""`. Chunk-2 judge should PASS (3/3) with
   the new values. Verify by running `python3 -m pytest
   tests/test_layout_paths.py tests/test_layout_paths_chunk2.py -v`.

6. **Is the suite green?** `python3 -m pytest -q` should show
   `197 passed, 3 skipped`. Note the interpreter version.

7. **Chunk-3 safety.** Does anything here make Chunk 3 (living-doc
   citation updates) harder or unsafe? Are stale old-layout citations
   properly fenced to Chunk 3?

## Rules

- Cite `file:line` for every finding. No finding without evidence.
- If you assert a site is missed or a path changes, SHOW the before and
  after strings.
- Verify claims yourself. The spec and this prompt may both be wrong.
- Distinguish severity honestly: `blocker` (chunk cannot close),
  `high`, `medium`, `low`, `nit`.
- If something is genuinely correct, say so briefly and specifically.
- Note the Python interpreter version in your report.

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

# Cross-family code review: chunk-D1-1 (layout path-root constants)

You are an independent Tier-2 reviewer. Adversarial, evidence-first.
Do not defer to the builder, the planner, or to any earlier review.

## What to review

Repo: `/Users/factory/work/adversarial-sprint-dev`
Branch: `factory/layout-refactor`
Build commit under review: **d5db8ff**
Spec: `planning/layout-refactor/CHUNK-1-SPEC.md`
Locked judge: `tests/test_layout_paths.py` (sha256 233eee9d…)
Diff of the build: `build.diff` in this directory.

Chunk 1 is meant to be a **behaviour-preserving no-op**: introduce
relative path-root constants + a `phase_path()` helper, route ~19
hardcoded phase-dir sites through them, add a shell mirror
(`tools/sprint_loop/paths.sh`), and move NO directories. Chunk 2 later
flips the constants' values and moves the tree.

## Your job — challenge these, in order

1. **Is it actually a no-op?** For every routed site, does the composed
   path resolve to the SAME string as before? Look hard at:
   - `EVIDENCE_ROOT = ""` and `PLANNING_ROOT = ""` — empty roots.
     `os.path.join("", "phase-4.5", ...)` swallows the empty part, but
     is that true at EVERY site, including f-strings, `--help` text,
     shell `${...}` expansion, and anything writing a manifest?
   - `BUILD_EVIDENCE_REL` — does it render identical bytes in argparse
     help and in every path it composes?
   - Any place a leading or doubled slash could appear.

2. **Did any site get MISSED, and does the judge actually catch misses?**
   Run your own grep for live `phase-[0-9]` path construction under
   `tools/`, `phase-*/`, `.github/`. The judge's residual scan uses two
   AST matchers (joined-literal substring, and a bare-segment regex
   scoped to `.join()` args / pathlib `/` operands). Probe it: can you
   construct a real unrouted site that this scan does NOT flag? A
   `%`-format, `.format()`, an f-string with the segment split, a
   `str.join`, a variable holding the segment, `pathlib.PurePath`,
   `os.sep.join`, a segment built by concatenation?

3. **`local_backend.py` bootstrap.** It inserts `tools/` on `sys.path`
   from a self-relative root, then imports `sprint_loop.config`
   unguarded at module level. Is the three-`dirname` depth right? Is
   the self-relative root correctly kept OUT of the composed paths
   (they must compose against the runtime `--framework-root`)? Can the
   two disagree in a way that breaks a real sprint?
   NOTE: this module cannot run standalone on this interpreter at all —
   it has a pre-existing `-> dict | None` annotation and Python here is
   3.9.6 (ledger KI-1). Do not report that as a build regression; DO
   tell us if it hides something.

4. **Judge quality.** The judge is planner-authored and locked; the
   executor did not modify it (verified). Is it strong enough to be the
   gate? Where is it weak, vacuous, or satisfiable by the wrong change?
   The planner already self-reported one unsatisfiable assertion
   (ledger SD-1). Assume there are more.

5. **Chunk-2 safety.** Does anything here make the Chunk 2 value-flip
   harder or unsafe? Constants that are relative segments, not absolute
   paths? Anything that bakes in today's layout beyond the constants?

## Rules

- Cite `file:line` for every finding. No finding without evidence.
- If you assert a site is missed or a path changes, SHOW the before and
  after strings.
- Verify claims yourself. The spec and this prompt may both be wrong.
- Distinguish severity honestly: `blocker` (chunk cannot close),
  `high`, `medium`, `low`, `nit`.
- If something is genuinely correct, say so briefly and specifically —
  do not pad. Use your own words; do not echo this prompt's phrasing.

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

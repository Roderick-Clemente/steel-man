# Cross-family code review: chunk-D1-2a (repair the five evidence-relative scripts)

You are an independent Tier-2 reviewer. Adversarial, evidence-first.
Do not defer to the builder, the planner, or to any earlier review.

## What to review

Repo: `/Users/factory/work/adversarial-sprint-dev`
Branch: `factory/layout-refactor`
Build commit under review: **<BUILD_COMMIT>**
Spec: `planning/layout-refactor/CHUNK-2a-SPEC.md`
2a judge: `tests/test_layout_paths_chunk2a.py`
  (sha256 `7289ca0967095fb4f9f2d45daf4637da77d556048e5a59664532d665fd89691c`,
  23 tests, locked at
  `tools/phase-1-locks/tests/test_layout_paths_chunk2a.py.lock.json`)

**This judge has been amended once already.** The first ratified version
(`3307020a…`, 16 tests) was defeated by three partial fixes: a dead
`envelope_path` with no `phase-N` prefix, a CWD-relative `open()` built with
`os.path.join` segments, and a `--locks-dir` default of
`os.path.join(_FRAMEWORK_ROOT, "LOCKS_ROOT")` — the quoted constant name. Each
was green against the old judge and each is now caught behaviourally, verified
against reproduced mutations. **Those three are closed; do not re-report
them.** Item 2 asks you for a *new* shape.
Chunk-1 judge: `tests/test_layout_paths.py` (sha256 `cb00dfac…`, skips post-flip)
Chunk-2 judge: `tests/test_layout_paths_chunk2.py` (sha256 `48a579f8…`)
Diff of the build: `build.diff` in this directory.

Suite interpreter: `/private/tmp/asprint-venv/bin/python` (3.13.3) on the
builder's machine. **This pin lives under `/tmp` and may not exist on yours** —
a previous reviewer found it absent and built its own venv, which is the correct
response. Build one, and state the path and version you used. Do not assume
`/usr/bin/python3` matches it: interpreter availability is machine-scoped, and
recording a bare rc without the interpreter has already produced one bad
evidence row (spec §2.4 K2).

chunk-D1-2 moved 617 tracked files out of the `phase-N/` silos and broke five
scripts that resolved paths relative to their own former location. Four fail
closed with `FileNotFoundError`. The fifth, `tools/phase-1-scripts/lock.py`,
fails **open** — it would write a lock manifest to a wrong directory and report
success. chunk-D1-2a repairs all five, a stale test fixture, a `.gitignore`
prose claim, and appends errata against the chunk-D1-2 findings.

## Your job — challenge these, in order

1. **Did the read path and the `envelope_path` write string land together?**
   This is the central risk in the chunk. For each of
   `tools/phase-3-gen/gen-telemetry.py`, `tools/phase-3.1-gen/gen-telemetry.py`,
   `tools/phase-4-gen/reconstruct-telemetry.py`, and
   `tools/phase-4-gen/gen-findings.py`: show the before and after strings for
   both the root resolution and every emitted path. A read-path fix without the
   matching write-string fix converts a loud rc=1 into telemetry rows carrying
   pointers to files that are not there — strictly worse than the bug it
   replaces. Confirm each emitted `envelope_path` resolves to a file that
   actually exists.

2. **Try to construct a partial fix that passes the judge.** Spend real effort
   here; it is the reason this chunk has a §4.7. The known case: repairing
   `reconstruct-telemetry.py:31-32` while leaving `:29`'s `REPO_ROOT` walking
   only one level up. That exits 0, emits no stale prefix, and satisfies an
   rc-based check — while `:157`'s `os.path.exists(RUNS_PATH)` guard reads zero
   existing rows and `:211`'s `open(RUNS_PATH, "w")` writes a truncated fork of
   the telemetry system of record to `tools/telemetry/runs.jsonl`. Verify:
   `telemetry/runs.jsonl` still has all its rows (it had 21 pre-chunk),
   `tools/telemetry/` does not exist, and no other partial-fix shape survives
   the judge. If you find one the judge misses, that is a blocker.

3. **Is `lock.py` actually fixed, and is judge immutability still enforced?**
   `tools/phase-1-scripts/lock.py:42` defaulted `--locks-dir` to
   `dirname(dirname(abspath(__file__)))/locks`, resolving to the nonexistent
   `tools/locks`. It must now derive from `sprint_loop.config.LOCKS_ROOT`.
   Check the writer and the reader agree: `lock.py` and
   `tools/phase-1-hooks/locked-test-guard.py` must resolve to the same
   location. Confirm the three existing manifests under
   `tools/phase-1-locks/tests/` were not moved, rewritten, or duplicated, and
   that `tools/locks` was not created. A lock writer and lock reader that
   disagree silently disable framework invariant 3.

4. **Is the 2a judge byte-unchanged?** Hash it yourself and compare to both the
   value above and the lock manifest. The builder may not modify the test that
   judges it (invariant 3). Also confirm `tests/test_layout_paths.py` is still
   `cb00dfac…` and `tests/test_layout_paths_chunk2.py` still `48a579f8…`, each
   matching its lock.

5. **Did paths route through the constants, or get re-hardcoded?** The four
   scripts broke because they hardcoded a layout. Fixing them by hardcoding the
   *new* layout reproduces the defect one move later. Every repaired path should
   resolve via `EVIDENCE_ROOT`, `BUILD_EVIDENCE_REL`, `BUILD_EVIDENCE_DIR`,
   `LOCKS_ROOT`, or `phase_path()` from `tools/sprint_loop/config.py`. Flag any
   new literal `evidence/phase-N/...` string in executable code.

6. **Is the suite green, and at the right counts?** Gate on the 2a judge in
   isolation: `pytest -q tests/test_layout_paths_chunk2a.py` must be
   **23 passed**. The full suite at the branch tip also contains the chunk-D1-3
   judge — 14 tests, **10 of them a deliberate valid RED** until chunk 3 is
   built — so expect roughly **10 failed / 224 passed / 3 skipped** overall and
   treat only the 2a number as this chunk's signal. The 224 is arithmetic
   (217 + 7 new), not a measurement: measure it and report what you get. If the
   numbers don't reconcile, say so rather than rounding to "green," and confirm
   every failure you see belongs to `test_layout_paths_chunk3.py`.

7. **Were the errata appended, not edited?** `FINDINGS-chunk-D1-2.md` is
   immutable under §5/§21, so §2.4's corrections belong in
   `planning/phase-4.5/LEDGER.md` as `ERRATUM: supersedes=…` rows — they are at
   `LEDGER.md:904-957`. Confirm zero deletions on both files across the 2a
   commits (`git log --numstat`), and that the findings file is byte-identical
   to the commit that created it — **`bc83471`, not `ee90061`**. An earlier
   version of this item said `git show ee90061:<path>`, which cannot work: the
   file did not exist at `ee90061`.

8. **Scope escapes.** This chunk moves nothing. Any `R` status line in
   `git show <BUILD_COMMIT> --name-status` is out of scope — the `LEDGER.md`
   rename belongs to Chunk 3, not here. Also confirm nothing was written under
   `evidence/phase-4.5/tokens/`; the builder does not hold the signing key and
   must not produce tokens (§22).

9. **Audit the spec itself for further false claims.** The spec already carries
   two errata written *against its own author*: the planner wrongly "corrected"
   the builder's rename count to 617 + 1 R089 (the truth is 618 R100 + 16 M),
   and mislabeled 3.9.6 as the suite interpreter. Both were caught by the
   builder or by measurement, not by review. Assume more remain. Check every
   line number, constant name, hash, and count the spec asserts, and report any
   that do not reproduce.

10. **Chunk-3 safety.** Chunk 3 renames `planning/phase-4.5/LEDGER.md` to
    `evidence/LEDGER.md` and updates living-doc citations. Does anything in this
    build make that harder or unsafe? Note that `tests/test_layout_paths.py:571`
    cites the old LEDGER path in a comment and is lock-frozen, so it is handled
    by `planning/PATH-REDIRECTS.md` rather than edited — confirm this build did
    not touch it.

## Rules

- Cite `file:line` for every finding. No finding without evidence.
- If you assert a site is missed or a path changes, SHOW the before and
  after strings.
- Verify claims yourself. The spec and this prompt may both be wrong.
- Distinguish severity honestly: `blocker` (chunk cannot close),
  `high`, `medium`, `low`, `nit`.
- If something is genuinely correct, say so briefly and specifically.
- Note the Python interpreter path and version in your report.
- **Do not run `tools/phase-3-gen/gen-telemetry.py` or
  `tools/phase-3.1-gen/gen-telemetry.py` at all — not even with `--dry-run`.**
  Neither parses argv. The flag is accepted silently, ignored, and the script
  performs its real truncating write to `telemetry/runs.jsonl`: the phase-3
  generator rewrites the whole file with its own 13 rows, so the live 21-row
  SoR becomes 13. There is no safe way to invoke them. Only
  `tools/phase-4-gen/reconstruct-telemetry.py` honours `--dry-run`, and it is
  the only one of the three you may run.

  This matters more than it looks. `telemetry/runs.jsonl` is gitignored
  (`.gitignore:44`), so a shrink appears in no porcelain, no diff, and no
  stat — you cannot detect that you caused it. Item 2 then instructs you to
  verify the SoR "still has all its rows (it had 21 pre-chunk)", so your own
  side effect presents as a confirmed §4.7 partial-fix hit against the build,
  and you would file a blocker against code that is correct. An earlier
  version of this rule said "without `--dry-run` where one exists", which
  could not be acted on: passing the flag to a script that ignores it is
  byte-indistinguishable from it being honoured.

- Do not commit, stage, or modify anything. You are read-only plus
  `Execute`; a review that mutates the artifact under review is void.

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

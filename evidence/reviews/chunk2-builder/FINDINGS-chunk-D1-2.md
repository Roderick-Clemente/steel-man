# chunk-D1-2 builder findings — for the close gate

Build commit: `ee90061`. Predecessor: `c63b776`.
Suite: **197 passed, 3 skipped** (`suite.out`).
Moves: **618 files, all `R100`** — 0 insertions, 0 deletions, so no
evidence byte changed (§5, §21). Mapper: `move-mapper.py`.

Everything below is something CHUNK-2-SPEC §2.1–§2.4 did **not**
enumerate. It is listed here rather than buried in the diff, because the
gate should grade the judgment calls, not discover them.

## 1. The destination rule the spec leaves ambiguous

§2.1 writes moves as `phase-1/build-evidence/ → evidence/phase-1/`,
which reads as "drop the leaf". PLAN §4:133-136 states the opposite as an
explicit **Rule**: leaf names are preserved. The two cannot both hold,
and phase-2/3/3.2 each have **two** source subtrees (`build-evidence/`
and `reviews/`) that would collide if leaves were dropped.

Resolution applied — **leaf preserved, except a leaf literally named
`evidence`, which the `evidence/` root absorbs.** Three independent
pins agree with this and no other reading:

| Pin | Requires |
|---|---|
| Chunk-2 judge (`TOKENS_ROOT`, `BUILD_EVIDENCE_DIR`) | `evidence/phase-4.5/tokens/`, `evidence/phase-4.5/build-evidence/` — leaves preserved |
| §2.3 CI fix `:192` | `planning/phase-3.2/reviews/review-prompt.md` — leaf preserved |
| PLAN §4:171 | phase-3.2 schema JSONs at `evidence/phase-3.2/` — leaf `evidence` absorbed |

## 2. `.gitignore` — §2.3's instruction REFUSED, not implemented

§2.3: "keep the existing `phase-*/build-evidence/r-*/` pattern and add
`evidence/*/build-evidence/r-*/`".

**There is no such pattern to keep.** `.gitignore` contains zero
`phase-*` or `build-evidence` patterns. The rule was removed
deliberately on 2026-08-13, and the ~20-line rationale still in the file
records why: a prefix-form directory exclude silently swept up the
chunk-D1-1-spec review envelopes that a *signed referee token* attested
to, and on a second machine those envelopes did not exist at all — the
only surviving trace was a commit message.

Adding `evidence/*/build-evidence/r-*/` reinstates that exact shape, and
directory-form excludes cannot be undone by a `!` negation. This is the
§7 silent-green class the file was edited to close.

**The executor did not add it.** A one-paragraph note in `.gitignore`
records the refusal at the point of use. If the planner still wants
scratch-tree ignoring, it needs a form that cannot match a reviewer
tree — which the removal note argues is not achievable by prefix.

## 3. Three files §2.1 has no destination for

§4.2 requires that no `phase-N/` dir remain tracked, so every file must
land somewhere. These have no enumerated home:

| File(s) | Classified as | Why |
|---|---|---|
| `phase-2/reviews/{plan-review-prompt,planner-prompt,round-1-prompt}.md` | `planning/phase-2/reviews/` | §2.1 routes `phase-2/reviews/` to evidence "envelope JSONs only" — there are **zero** envelope JSONs in it; all three files are prompts. §2.1 itself classifies `phase-3.2/reviews/review-prompt.md` as planning. |
| `phase-3/reviews/.gitkeep` | `evidence/phase-3/reviews/` | Sole content of the dir; it exists to hold open the reviews **evidence** tree §2.1 routes to `evidence/phase-3/`. |
| `phase-3.2/reviews/RUN-COMMANDS.md` | `planning/phase-3.2/reviews/` | Unenumerated. A doc, sitting beside `review-prompt.md`, which §2.1 calls planning explicitly. |

## 4. `pytest.ini` also excludes `tests/fixtures`

§2.3 lists only `norecursedirs` losing `phase-N` and gaining `evidence`
+ `tools/phase-5-scripts`. But §2.1 moves `phase-1/fixtures/` to
`tests/fixtures/phase-1/`, i.e. **inside `testpaths`**, and
`invalid-red/*.py` are deliberately-invalid negative fixtures for
`valid-red.py` — one of them carries an intentional unclosed-paren
`SyntaxError`. Collection aborts the whole run:

```
ERROR tests/fixtures/phase-1/invalid-red/test_syntax_error.py
E   SyntaxError: '(' was never closed
!!! Interrupted: 4 errors during collection !!!
```

They are inputs, never tests. Without this exclusion §2.1's mandated
move makes the suite uncollectable, so the addition is load-bearing, not
tidying.

## 5. Two split-segment sites missing from §2.4, plus the stub repo

§2.4's site list catches single-literal paths. Two sites build the path
from separate segments and so are invisible to a substring sweep:

- `tests/test_plan_lint.py:147` — `_REPO_ROOT / "phase-4.5" / "tokens" / …`
- `tests/test_sprint_loop.py:1161` — `tmp_path / "fw" / "phase-4.5" / "build-evidence"`

This is idiom **D/I** from the 12 the strengthened matcher was hardened
against — the same blind spot, in a file the matcher does not scan.
Worth noting: `ROUTED_PY_FILES` covers 9 modules, and neither test file
is among them, so the judge could not have caught these. The **suite**
caught both. That is the §7 argument working in the other direction.

`tests/fixtures/plan-lint/repo/` is also a stub repo mirroring the
framework layout, so §2.4's fixture rewrite is unsatisfiable without
moving `repo/phase-4.5/tokens/` → `repo/evidence/phase-4.5/tokens/` and
updating the 14 `phase-4.5/tokens/` citations in the plan fixtures that
lint against it.

## 6. `plan-lint.py:1151` needed a lookbehind

§2.3 says to add `evidence` and `planning` to the unanchored regex. Done
literally, the `evidence` alternative matches **mid-token**:
`tools/phase-3.2-evidence/local_backend.py` yields a warning that
`evidence/local_backend.py` does not exist. Four false positives on
`PLAN.md` immediately; Chunk 3 will multiply that, since 31 tracked
files cite `phase-3.2/evidence` and all become `tools/phase-3.2-evidence`.

Added `(?<![\w./-])` so only a path **start** matches: 24 → 20 warnings,
suite unaffected, `PASS` preserved.

## Known issues carried forward (NOT fixed here — Chunk 3 fence)

Stale old-layout prose survives in non-judged locations. The residual
matcher skips comments and docstrings by design, so none of these are
gate failures, and §5 fences living-doc citations to Chunk 3:

- `tools/sign_chunk_token.py:6,135`, `tools/chunk_sequence_gate.py`
  docstrings. chunk-D1-1's plan intended to reword these to name the
  constant; they still spell the old path. Neither reaches `--help`
  (both use a literal `description=`), so `--help` bytes are unaffected.
- `tools/OPERATING-RULES.md` (7 sites), `tools/sprint_loop/prompts/*.md`,
  `tools/sprint_loop/__init__.py`, and the docstrings of the newly-moved
  scripts under `tools/phase-1-scripts/`, `tools/phase-1-probes/`,
  `tools/phase-3.2-evidence/`, `tools/phase-5-scripts/`.
- `tools/phase-4-gen/gen-findings.py` embeds `phase-1/hooks/` in
  historical finding rows — that is recorded data about where a defect
  was found, not a live path. It should probably stay as-is.
- `tests/fixtures/plan-lint/PLAN-5.1-v{5,6}.md` cite
  `phase-4.5/KNOWN-ISSUES.md` and `phase-4.5/prompts/`. Untouched: the
  stub repo never contained either, so behaviour is unchanged.

## Verification actually run

| Check | Result |
|---|---|
| §4.1 full suite | 197 passed, 3 skipped (`suite.out`) |
| Chunk-2 judge runs (not skips) | 3/3 **PASSED** |
| Chunk-1 judge | 3/3 SKIPPED as designed |
| Both judges byte-untouched | `cb00dfac` / `48a579f8`, matching locks |
| §4.2 allowlist | `test_repo_layout.py` green; zero tracked `phase-*` paths; zero `phase-*` dirs on disk |
| §4.3 constants resolve | Chunk-2 judge asserts all 7 roots `isdir` |
| §4.4 plan-lint | `PASS with 20 warning(s)`, rc=0 |
| §4.5 history | `git log --follow` crosses the move for 11 files spanning every destination class |
| Evidence bytes | 618/618 renames `R100`, 0 insertions / 0 deletions |
| `local_backend.py --help` | rc=0 at `tools/phase-3.2-evidence/` |
| `bash -n` fire script | rc=0 at `tools/phase-5-scripts/` |
| `paths.sh` contract | roots non-empty, `$PHASE5_SCRIPTS_ROOT/envelope-manifest.py` exists |
| Stronger-matcher probe | 0 residual hits / 9 files; 12/12 idioms flagged; 0 false positives |
| `--help` byte-diff vs `c63b776` | only intended path changes (`sprint-loop.py`, `chunk_sequence_gate.py`); `sign_chunk_token.py` and `orchestrate-review.py` identical |

The committed chunk-D1-1 probe at
`r-chunk1-builder-verify-20260814/stronger-matcher-probe.py` hardcodes
the pre-move `local_backend.py` path and now raises `FileNotFoundError`.
It was **not** edited — it is a committed evidence byte (§5). A patched
copy was run out-of-tree and is preserved here as
`stronger-matcher-probe-chunk2.py`.

## Seat fences held

No `droid exec` fired. No `EVIDENCE_SIGNING_KEY` held. Nothing written
under `evidence/phase-4.5/tokens/`. Neither judge edited. The close gate
is the planner's to fire (Ruling 3: `kimi-k3` + `minimax-m3`, sequential,
via `tools/orchestrate-review.py`).

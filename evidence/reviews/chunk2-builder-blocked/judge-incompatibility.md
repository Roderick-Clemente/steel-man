# chunk-D1-2 BLOCKED — locked Chunk-1 judge is incompatible with Chunk 2's deliverable

Builder seat. Measured at `409c62c` (judge `10f9e780`, suite 197 green,
Python 3.13.3). No repo files were modified to produce this; the experiment
ran in a detached `git worktree` that has been removed.

## Claim

`CHUNK-2-SPEC.md` §4.1 ("197 tests, all green") and §2.2 (flip the constant
VALUES) are **mutually unsatisfiable** while `tests/test_layout_paths.py` is
locked at `10f9e780`. The Chunk-1 judge asserts the **old values literally**,
not merely that the constants resolve.

## Method

Detached worktree at HEAD. Applied only §2.2's 7-constant flip, then the two
`git mv`s that touch the judge's own path constants. Ran the judge.

## Result — all 3 locked tests fail

After the flip alone (no moves), 2 of 3 fail:

```
AssertionError: assert 'evidence' == ''                       # :422 EVIDENCE_ROOT
AssertionError: assert
  - /…/phase-4.5/tokens/chunk-5a.token.json
  + /…/evidence/phase-4.5/tokens/chunk-5a.token.json          # :446 phase_path
2 failed, 1 passed
```

After `git mv phase-3.2/evidence/local_backend.py tools/phase-3.2-evidence/`
and `git mv phase-5/scripts/fire-design-review.sh tools/phase-5-scripts/`,
the third fails too:

```
AssertionError: missing: /…/phase-3.2/evidence/local_backend.py
3 failed
```

## Why this is the planner's write, not mine

Framework invariant #3: the executor must not author the judge that grades its
own work. `tests/test_layout_paths.py` is planner-authored and content-locked
at `phase-1/locks/tests/test_layout_paths.py.lock.json`. Per CHUNK-1-SPEC §3.4
as reworded, the builder raises `BLOCKED:` rather than editing. I have not
touched the file.

## Note on §4.3's description

§4.3 says the Chunk-1 judge "refuses if any constant points to a nonexistent
path", implying an existence check that would survive the flip. The test as
written does assert existence — but only *after* asserting exact equality
against the old values (`:422-433`), so the equality assertions fail first.
§4.3's description does not match the test's implementation.

## Precise re-authoring surface (7 sites, all in tests/test_layout_paths.py)

| line | current | needs |
|---|---|---|
| 422 | `EVIDENCE_ROOT == ""` | `== "evidence"` |
| 423 | `PLANNING_ROOT == ""` | `== "planning"` |
| 426-430 | `expected` dict holds old 5 values | new 5 per §2.2 |
| 445 | `want_token` under `phase-4.5/tokens` | under `evidence/phase-4.5/tokens` |
| 449-451 | `phase_path(…,"scripts","lock.py")` under `phase-1/scripts` | under `tools/phase-1-scripts` |
| 79 | `ROUTED_PY_FILES` has `phase-3.2/evidence/local_backend.py` | `tools/phase-3.2-evidence/local_backend.py` |
| 86 | `FIRE_SCRIPT = phase-5/scripts/…` | `tools/phase-5-scripts/…` |
| 525 | `lb_rel = phase-3.2/evidence/local_backend.py` | `tools/phase-3.2-evidence/local_backend.py` |

Two further items for the planner to decide, not for me:

1. **`_FORBIDDEN_SUBSTRINGS` (`:93-100`) goes stale after the flip.** It lists
   `phase-1/scripts`, `phase-1/locks`, `phase-3.2/evidence`, `phase-4.5/tokens`,
   `phase-4.5/prompts`, `phase-4.5/build-evidence`. Post-move, those strings
   name dirs that no longer exist, so the residual scan stops being a
   regression guard and starts being dead weight. The Chunk-2 analogue would
   forbid the *new* joined roots appearing unrouted.
2. **Whether this is a re-lock of the Chunk-1 judge or a new Chunk-2 judge.**
   A re-lock destroys the ability to re-verify Chunk 1 independently, which
   matters because the chunk-D1-1 gate is still formally open (SPLIT, no §8
   override issued). A separate `tests/test_layout_paths_chunk2.py` preserves
   both. The suite count changes either way, so §4.1's "197" also needs a
   number the planner intends.

## Builder status

Not blocked on anything else. The move inventory is read and the §2.2 values
are confirmed to match what I derived independently. I can execute the whole
build the moment the judge question is settled.

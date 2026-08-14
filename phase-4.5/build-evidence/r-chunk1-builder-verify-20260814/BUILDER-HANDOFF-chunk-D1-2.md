# Builder handoff — chunk-D1-2 (layout refactor, Chunk 2)

Paste everything below the line into a fresh session. It is self-contained.

---

You are the **builder/executor seat** on the `adversarial-sprint` framework repo.
Load the `adversarial-sprint` skill first, then read `tools/OPERATING-RULES.md`
(one file read — §7, §11, §13, §20, §22 dominate this chunk's risk surface).

## Your seat, and what it forbids

You **build, verify, commit, push, and post ledger rows**. You do not review your
own work and you do not close your own chunk.

Hard fences — these are framework invariants, not preferences:

- **Never edit `tests/test_layout_paths.py`.** Planner-authored, content-locked
  (`phase-1/locks/tests/test_layout_paths.py.lock.json`). Invariant #3 forbids
  the executor authoring its own judge. If an assertion looks wrong, post
  `BLOCKED:` with evidence instead of editing. This applies even if you can see
  the fix — writing the matcher that grades you *is* the breach.
- **Never fire `droid exec`** against reviewer models (§22). You hold no
  `EVIDENCE_SIGNING_KEY`, write nothing under `phase-4.5/tokens/`, sign nothing.
  You may post `REVIEW REQUEST:` rows; the planner/referee fires and signs.
- **Never post a `REVIEW REQUEST` whose `paths=` points at an envelope that does
  not exist on disk.** That is the self-declaration §21 forbids. Record
  `NOT FIRED:` instead so the absence is explicit.
- **Do not archive, delete, or "tidy" untracked files.** Reviewer models write
  stray artifacts into the tree (grok left a `build.diff.out` in the repo root
  during the Chunk-1 round); `orchestrate-review.py`'s stray-write check catches
  them. They are evidence. Leave them untracked and report them; do not delete.

## Repo state

| Fact | Value |
|---|---|
| Repo | `~/Work/adversarial-sprint` (only clone on this machine) |
| Branch | `factory/layout-refactor` |
| HEAD at handoff | `af94f71` |
| Push remote | **`dev`** (`Roderick-Clemente/adversarial-sprint-dev`) |
| `origin` | `Roderick-Clemente/adversarial-sprint` — **RETIRED, do not push** |
| Python | `/tmp/adv-venv/bin/python` — system `python3` lacks pytest. If the venv is gone, recreate and `pip install pytest pyyaml` |
| Suite | **197 passed**, 0 failed (re-run on 3.13.3; planner reports green on 3.9.6, CI is 3.12) |
| Judge sha256 | `10f9e780b8c40db6d0acf038c4d886faac538756424dd299d1209949e309e2bc` — matches its lock. **This is the STRENGTHENED matcher**, not the `233eee9d` one Chunk 1 was graded by |

Verify before you start: `git rev-parse --short HEAD`, `git status --porcelain`
(expect clean), `/tmp/adv-venv/bin/python -m pytest -q`. Do not trust any number
in this document you have not re-run.

## What Chunk 1 shipped — this is the contract Chunk 2 MUST NOT regress

Commits: `d5db8ff` (build) → `fa0cbd6` (ledger) → `5cd2ac4` (nit fixes) →
`54629f4` (ledger) → `bd70d10` (builder verification evidence).

In `tools/sprint_loop/config.py`, seven layout roots as **RELATIVE SEGMENTS**
plus a helper:

```python
EVIDENCE_ROOT = ""            # → "evidence" in Chunk 2
PLANNING_ROOT = ""            # → "planning" in Chunk 2
TOKENS_ROOT = os.path.join("phase-4.5", "tokens")
PROMPTS_ROOT = os.path.join("phase-4.5", "prompts")
SCRIPTS_ROOT = os.path.join("phase-1", "scripts")
LOCKS_ROOT = os.path.join("phase-1", "locks")
EVIDENCE_CODE_ROOT = os.path.join("phase-3.2", "evidence")

BUILD_EVIDENCE_REL = os.path.join("phase-4.5", "build-evidence")   # bare segment
BUILD_EVIDENCE_DIR = os.path.join(EVIDENCE_ROOT, BUILD_EVIDENCE_REL)  # root-composed

PHASE_ROOTS = {"evidence":…, "planning":…, "tokens":…, "prompts":…,
               "scripts":…, "locks":…, "evidence-code":…}

def phase_path(framework_root: str, kind: str, *parts: str) -> str
```

**Four binding invariants, each of which cost a review round to establish:**

1. **The constants are relative segments. `framework_root` is supplied at call
   time.** Never `os.path.join(framework_root, …)` at module level —
   `framework_root` does not exist in module scope (`NameError` at import), and
   if it did, `phase_path` would compose it a second time and double the root.
   Grok raised this as a **high** against the CHUNK-2-SPEC draft.
2. **`phase_path` has no `phase=` parameter and `framework_root` is the leading
   positional.** The judge pins this signature.
3. **`BUILD_EVIDENCE_REL` and `BUILD_EVIDENCE_DIR` are different things.** REL is
   the bare segment and mirrors the shell variable of the same name in
   `tools/sprint_loop/paths.sh` **exactly, in both chunks**. DIR is REL under the
   evidence root and is what prose means by "the build-evidence dir"; it grows
   the `evidence/` prefix at the flip. Collapsing them back into one name
   re-creates the double-apply trap gemini flagged.
4. **`phase-3.2/evidence/local_backend.py`'s three-`dirname` bootstrap depth is
   correct and MUST NOT be "fixed".** The Chunk-2 target sits at the same depth.
   Its self-relative root exists **only** to put `tools/` on `sys.path`; the
   routed paths compose against the runtime `--framework-root` argument. The two
   are permitted to disagree. The import is unguarded and module-level on
   purpose — lazy or `try/except ImportError` passes `--help` and dies at sprint
   runtime, which is the §7 silent-green class.

Also shipped: `tools/sprint_loop/paths.sh` (exports `EVIDENCE_ROOT`,
`BUILD_EVIDENCE_REL`, `PHASE5_SCRIPTS_ROOT`), sourced from
`phase-5/scripts/fire-design-review.sh` anchored on `$REPO_ROOT` — **not**
`$(dirname "$0")/../sprint_loop`, which resolves to a nonexistent path and
hard-fails under `set -euo pipefail`.

## Gate status

chunk-D1-1's code gate came back **SPLIT** — grok `ACCEPT-WITH-NITS`, gemini
`REJECT`. 14 findings; only 2 were builder-owned and **both are fixed** in
`5cd2ac4`. The referee signed a split attestation at
`phase-4.5/tokens/chunk-D1-1-code.token.json` **in the referee repo** (commit
`92cbc44`) and appended to `STEER.md`, which is gitignored here.

**Status of the override — be precise about this.** The operator overruled the
SPLIT verbally, and the referee certified the override is *rationally defensible*
(the builder probe proved zero residuals under a stronger matcher; gemini's
`high` was against the judge, not the builder's code). But **no §8 operator
override has been formally issued**, so the chunk-D1-1 code gate is still
technically **open**. The planner has nonetheless cleared the builder to start
chunk-D1-2. Build, but do not describe chunk-D1-1 as accepted, and do not
manufacture the override yourself.

Also: the attestation lives in the referee's repo, so it is **not reachable from
this clone**. `tools/chunk_sequence_gate.py` will not find a chunk-D1-1 token —
expect a nonzero exit if you run the start gate. Raise it with the operator
rather than fabricating a token.

## Findings NOT yours — do not "helpfully" fix these

| Owner | Finding | State |
|---|---|---|
| Planner (CHUNK-2-SPEC) | grok **high**: §2.2 drafted module-level `os.path.join(framework_root, …)` | **RESOLVED** in `af94f71` — constants are now independent relative segments, VALUES only |
| Planner (judge) | gemini **high** + grok medium: 5 residual-matcher blind spots | **RESOLVED** in `af94f71` — re-locked `233eee9d` → `10f9e780` |
| Planner (judge) | grok medium ×2: `paths.sh` values only non-empty-checked; `BUILD_EVIDENCE_REL` never value-asserted | check whether `af94f71` covered these; if not, still planner's |
| Not a defect | grok low: `phase_path(fw,"evidence","phase-4.5","build-evidence",run_id)` keeps segments at the call site | §2.2 **requires** the segment-preserving form. Do not "simplify" it |

**The judge you will be graded by is now strictly stronger than the one Chunk 1
passed.** It catches all 12 idioms: split-segment f-strings, bare-segment concat,
a variable holding a segment, `os.sep.join` with a list arg, and `PurePath`
constructors — and it keeps the 6 telemetry/HMAC label sites unflagged. Assume
nothing sneaks past it.

The builder-side probe at
`phase-4.5/build-evidence/r-chunk1-builder-verify-20260814/` independently found
**0 residuals** across the 9 routed files, and the planner's authored-then-
compared judge agreed on all 12 cases — with one disagreement resolved in the
probe's favour (case F, `root + "phase-1" + "scripts"`, needed their check 3).
Keep re-running the probe after each Chunk-2 edit as an early-warning system. It
is a measuring instrument, **not** a judge implementation to adopt.

## Your job: chunk-D1-2

**Authoritative spec:** `planning/layout-refactor/CHUNK-2-SPEC.md` at `af94f71`.
Parent `PLAN.md`. Spec wins on conflict.

The §2.2 constant flip, verbatim from the corrected spec — all relative segments,
no `framework_root` at module level, and the 7 roots must not reference each
other:

```python
EVIDENCE_ROOT      = "evidence"
PLANNING_ROOT      = "planning"
TOKENS_ROOT        = os.path.join("evidence", "phase-4.5", "tokens")
PROMPTS_ROOT       = os.path.join("planning", "phase-4.5", "prompts")
SCRIPTS_ROOT       = os.path.join("tools", "phase-1-scripts")
LOCKS_ROOT         = os.path.join("tools", "phase-1-locks")
EVIDENCE_CODE_ROOT = os.path.join("tools", "phase-3.2-evidence")
```

`TOKENS_ROOT` and `PROMPTS_ROOT` spell `"evidence"`/`"planning"` **literally**,
not as `os.path.join(EVIDENCE_ROOT, …)` — coupling them risks doubling the root.
`BUILD_EVIDENCE_REL` is unchanged; `BUILD_EVIDENCE_DIR` stays derived and
auto-flips. `default_evidence_dir` needs **no change** — it already composes
segment-preserving through `phase_path`.

Chunk 2 = `git mv` the phase dirs to taxonomy homes + flip the constant VALUES +
fix linters/CI/fixtures. Moves and flip must land **together**: a move without
the flip breaks every path.

Target taxonomy (confirm against §2.1/§2.3 before acting):
`phase-1/scripts` → `tools/phase-1-scripts`, `phase-1/locks` → `tools/phase-1-locks`,
`phase-3.2/evidence` → `tools/phase-3.2-evidence`, `phase-5/scripts` →
`tools/phase-5-scripts`, `phase-1/fixtures` → `tests/fixtures/phase-1`, plus
`evidence/` and `planning/` roots becoming non-empty.

**Blast radius — measured at `bd70d10`, and much wider than Chunk 1's 9 files:**

| old root | tracked files referencing it |
|---|---|
| `phase-1/scripts` | 45 |
| `phase-3.2/evidence` | 31 |
| `phase-1/locks` | 25 |
| `phase-5/scripts` | 7 |
| `phase-1/fixtures` | 7 |

Chunk 1 was safe with a weak residual scan because nothing moved — a missed site
still resolved. **Chunk 2 flips values and runs `git mv`, so a missed site
breaks.** That is why the judge fix gates the close.

`pytest.ini` and `tests/test_repo_layout.py` both pin top-level layout. Both were
fenced in Chunk 1 and **legitimately change here** (`ALLOWED_TOP_LEVEL`,
`testpaths`), as does `tools/plan-lint.py`'s valid-prefix regex.

## Verify — run it, never assert it

1. `/tmp/adv-venv/bin/python -m pytest -q` → **197 green**. Chunk 2 adds no tests.
2. `git status --porcelain` → moves appear as **`R`** entries. Unlike Chunk 1,
   `R` entries are expected and required here; `git log --follow` on a moved file
   must still reach its history.
3. Constants resolve to the NEW paths; `phase_path` output is the new tree.
4. `bash -n phase-5/scripts/fire-design-review.sh` (at its new path) and the
   `paths.sh` contract: source it, assert `PHASE5_SCRIPTS_ROOT` and
   `BUILD_EVIDENCE_REL` non-empty and `$PHASE5_SCRIPTS_ROOT/envelope-manifest.py`
   exists.
5. `/tmp/adv-venv/bin/python <new-path>/local_backend.py --help` → exit 0.
6. `tools/plan-lint.py` accepts the new prefixes.
7. Re-run the stronger-matcher probe → still 0 residuals.
8. Byte-diff `--help` surfaces against a pristine worktree of the prior commit:
   `git worktree add --detach /tmp/base <sha>`. Chunk 2 **does** legitimately
   change these bytes (paths move), so read the diff and confirm every change is
   an intended path change and nothing else.

## Commit + handoff

Push to **`dev`**. Post to `phase-4.5/LEDGER.md`: `VALIDATE COMPLETE:` with the
suite number and the judge sha256, then either a `REVIEW REQUEST:` **once real
envelopes exist on disk**, or `NOT FIRED:` recording the absence. Sign nothing.

**You do not fire the close gate.** Per Ruling 3, builder-authored code is fired
by the **planner**: validators `kimi-k3` + `minimax-m3`, sequentially, via
`tools/orchestrate-review.py`, every envelope committed, LEDGER rows recorded.
Your job ends at green-and-committed; hand off and let them fire.

If anyone proposes a hand-rolled `droid exec` instead, push back: hand-rolling
already burned ~19K tokens rediscovering two documented failures — a missing
`--auto`/`--enabled-tools` and a missing `DROID_MODEL_ID` (which
`tools/run-with-model.sh` refuses without). The wrapper also adds locked-test
verification, stray-write detection, retries, and family-distinctness checks.

## Stop conditions — post `BLOCKED:` with evidence

- Suite still red after one bounded fix attempt.
- The locked judge denies a write you believe you need.
- A spec/PLAN contradiction you cannot resolve.
- Any move would lose git history.

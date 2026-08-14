# CHUNK-2a-DRAFT (builder) — post-move operational-code paths + closed-gate nits

**Status: builder review note + evidence record. This is not a spec.** The
builder seat authored it at the planner's request to carry forward the nits
from the chunk-D1-2-code gate. The planner authors `CHUNK-2a-SPEC.md`; the
planner fires the gate. Nothing here is a fence the executor may treat as
authority.

**Superseded in part.** `planning/layout-refactor/CHUNK-2a-SPEC.md` was
authored concurrently by the planner and already covers §2.1–§2.4 of this
draft, in places more precisely (it names `reconstruct-telemetry.py:29`
`REPO_ROOT` as the root cause and requires CWD-independence in its judge).
Where the two overlap, **the spec governs.** This draft is retained for two
reasons: it is the measurement record behind the spec's claims, and §6 carries
findings the spec does not yet reflect. **§6.5 and §6.6 are blocking for
the spec, not for the build** — both should be resolved before the judge locks.

**Provenance.** Both verdicts ACCEPT-WITH-NITS on build `ee90061`, two
distinct families, gate CLOSED at `3a6b76f`:

| Reviewer | session_id | envelope sha256 |
|---|---|---|
| `kimi-k3` | `547c565c-370d-4106-94ec-a4c43268abd5` | `8b503d93290bd56fbb03cc323ce3129dbe5b3aa7cb91414ff9a342d3d1383e46` |
| `minimax-m3` | `f4cece0d-8e8b-46b0-b97a-6ccd41b761d4` | `f496c1d4389b725897f492b4290f1cdea80d2e475d43cd5184b3005d13088c8e` |

Envelopes on disk at
`evidence/phase-4.5/build-evidence/r-chunk2-code-20260814-0319/code/`.

---

## 1. Problem statement (§13)

Chunk 2 moved 618 files into the new taxonomy and flipped the seven root
constants. Every path that resolved through those constants followed the
move. **Paths that resolved self-relatively or CWD-relatively did not.**

Four scripts under `tools/phase-{3,3.1,4}-gen/` locate their evidence by
`os.path.dirname(__file__)` or by a bare CWD-relative `open()`. Pre-move
they sat beside the evidence they read. Post-move they sit under `tools/`
and the sibling is gone. All four are regressions introduced by chunk 2 —
established below against the predecessor commit, not asserted.

Chunk 2's spec could not have caught them: §2.4 enumerates exactly one
code-output path. Chunk 3 cannot absorb them: its §2.1 allowlist is
markdown-only and its §4.2 verification greps `--include='*.md'`. Routing
four `.py` files into a markdown-only chunk is a category error, and it
would destroy the property that makes chunk 3 auditable — that it is a
mechanical, greppable citation sweep. Hence a follow-on chunk.

This chunk also carries the closed-gate items that cannot be fixed in
chunk 2 without invalidating the diff both reviewers attested to (§18.2:
one chunk, one commit).

---

## 2. Surface touched

### 2.1 Four evidence-relative scripts — THREE coupled edits each

**The three edits per script are not separable.** Each script has a read
root, an `envelope_path` string it writes into telemetry, and an output
root. Fixing any subset creates a worse defect than the one it repairs;
§2.1 must be applied per-script as an atomic unit. The evidence for that
claim is §6.1 — it is the reason this section is structured by script
rather than by defect type.

| # | File | Read root | `envelope_path` write | Output root |
|---|---|---|---|---|
| 1 | `tools/phase-3-gen/gen-telemetry.py` | `:22` | `:101` | `:23` |
| 2 | `tools/phase-3.1-gen/gen-telemetry.py` | `:21` | `:106` | `:22` |
| 3 | `tools/phase-4-gen/reconstruct-telemetry.py` | `:31`, `:32` | `:172`, `:180` | `:29`→`:30` |
| 4 | `tools/phase-4-gen/gen-findings.py` | `:153`, `:190`, `:235`, `:271` | — | `:299` |

Current values and required destinations:

**1 — `tools/phase-3-gen/gen-telemetry.py`**
- `:22` `EVID = os.path.join(os.path.dirname(__file__), "build-evidence")`
  resolves to `tools/phase-3-gen/build-evidence/` (does not exist).
  Evidence now lives at `evidence/phase-3/build-evidence/`.
- `:23` `OUT = …/os.pardir/"telemetry"/"runs.jsonl"` resolves to
  `tools/telemetry/runs.jsonl`. **`tools/telemetry/` does not exist**; the
  real telemetry SoR is the repo-root `telemetry/runs.jsonl`.
- `:101` writes the literal `"phase-3/build-evidence/" + fname` into the
  row's `envelope_path` field.

**2 — `tools/phase-3.1-gen/gen-telemetry.py`** — identical shape at
`:21` / `:22` / `:106`, evidence at `evidence/phase-3.1/build-evidence/`.

**3 — `tools/phase-4-gen/reconstruct-telemetry.py`**
- `:29` `REPO_ROOT = normpath(dirname(__file__) + os.pardir)`. Pre-move
  this was the repo root; post-move it is **`tools/`**. This single line
  is the root cause of both the read failure and the silent-green in §6.1.
- `:31`/`:32` `PHASE2_EVID`/`PHASE3_EVID` compose `phase-2|3/build-evidence`
  off `REPO_ROOT` → now `tools/phase-2/build-evidence/`.
- `:30` `RUNS_PATH` composes off `REPO_ROOT` → `tools/telemetry/runs.jsonl`.
- `:172`/`:180` f-strings write `phase-2|3/build-evidence/{fname}`.

**4 — `tools/phase-4-gen/gen-findings.py`** — four **CWD-relative**
`open()` calls, so behaviour depends on the invoking directory:
- `:153` `phase-3.2/reviews/roadmap-review-cross-family-findings.json`
- `:190` `phase-3.2/reviews/roadmap-review-v2-cross-family-findings.json`
- `:235` `phase-4/post-v3-review-{name}-envelope.json`
- `:271` `phase-4/track-execution-review-{name}-envelope.json`

Destinations verified on disk: `evidence/phase-3.2/reviews/` and
`evidence/phase-4/`. Output `:299` is CWD-relative `telemetry/findings.jsonl`
— correct only when run from the repo root, and so the same fragility class
even though it currently resolves.

**Recommended form (planner's call).** Resolve against the framework root
derived from `__file__`, then compose through `sprint_loop.config` rather
than re-hardcoding the new layout — otherwise chunk 2's defect recurs on
the next move:

```python
_FW_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVID = phase_path(_FW_ROOT, "evidence", "phase-3", "build-evidence")
```

These are standalone scripts with no `sprint_loop` import today. The
bootstrap pattern chunk 1 established for `local_backend.py` (unguarded,
module-level `sys.path` insert of `<root>/tools`, then a plain import with
`# noqa: E402`) applies unchanged and is the precedent to follow. If the
planner prefers to keep them stdlib-only, a literal `"evidence"` prefix
works but must be flagged as a known re-break site for any future move.

### 2.2 `tests/test_sprint_loop.py:1119-1120` — third split-segment site

```python
(tmp_path / "fw" / "phase-1" / "scripts").mkdir(parents=True)
(tmp_path / "fw" / "phase-3.2" / "evidence").mkdir(parents=True)
```

→ `"tools" / "phase-1-scripts"` and `"tools" / "phase-3.2-evidence"`.

Found by `kimi-k3`; confirmed on disk. My chunk-2 Finding 5 enumerated
**two** split-segment sites and there are **three** — the third sits in the
same dry-run test function ~40 lines above one I did fix. Idiom D/I again.

Not a failure today: `_validate_config` only requires `tools/sprint_loop`,
so these `mkdir`s create directories nothing reads and the test passes
regardless. That is precisely why it needs fixing — the fixture no longer
represents the layout the code under test composes, which is the §7
silent-green shape in a test rather than in production. Neither judge can
catch it: `ROUTED_PY_FILES` covers 9 modules and no test file is among them.

**Alternative worth the planner's consideration:** delete both `mkdir`s as
vestigial rather than update them. If nothing reads the directories, a
fixture that creates them at the *new* paths is still fiction, just
better-aligned fiction. Updating is the lower-risk choice and what I'd
default to; deleting is the more honest one.

### 2.3 `.gitignore:79` — one sentence, tightened

Current text:

> Directory-form excludes also cannot be undone with a `!` negation, so
> there was no way to re-include an envelope without `-f` on every single
> commit.

`minimax-m3` flagged this as technically false. **It is right that the
sentence is too broad, and wrong in the example it offers.** I tested all
four forms with `git check-ignore -v` against an exclude of
`ev/*/be/r-*/`:

| Form | Result |
|---|---|
| exclude only | ignored |
| `+ !ev/p/be/r-1/keep.json` (file-level — minimax's suggestion) | **still ignored** |
| `+ !ev/p/be/r-1/` (directory-level) | **not ignored** |
| `+ !ev/p/be/r-1/` `+ !ev/p/be/r-1/**` | ignored again |

So directory-form excludes *can* be undone — by a directory-form negation
naming the exact run-id, and only that form. The file-level negation
minimax proposed is the classic gotcha and does not work.

**The refusal stands, on minimax's own recommended reasoning**: re-inclusion
requires enumerating every run-id directory as its own negation at the
moment it is created, which is unmaintainable across a growing corpus and
fails silently when someone forgets. Only the over-broad sentence changes.
Proposed replacement:

> A directory-form exclude can only be undone by a directory-form `!`
> negation naming each run-id explicitly — a file-level negation inside an
> excluded directory does not re-include it. That means re-inclusion has to
> be maintained by hand, per run, forever, and fails silently when missed.

`.gitignore` is a live config file, not an evidence byte, so this is
editable — unlike §2.4's items.

### 2.4 Spec errata — corrections, not edits

**(a) `CHUNK-2-SPEC.md` §2.4, `local_backend.py:76,375`.** Confirmed stale.
`grep -n verify-green tools/phase-3.2-evidence/local_backend.py` returns
`6, 96, 100, 101, 111, 317, 318, 407` — not 76 or 375. `:101` already
composes via `phase_path(framework_root, "scripts", …)` and `:407` via
`SCRIPTS_ROOT`; both were routed in chunk-D1-1. `:6` is a module docstring.
The instruction was already satisfied before chunk 2 began. Recommend
dropping the line numbers and stating "no code edits required here —
routed in chunk-D1-1; `:6` docstring deferred."

**(b) `FINDINGS-chunk-D1-2.md` is a committed evidence byte (§5) and MUST
NOT be edited.** Three of its claims need erratum rows recorded elsewhere
— the LEDGER is the natural home, and posting them is the planner's or
referee's call, not the builder's:

| Claim | Correction |
|---|---|
| §"Verification actually run": `local_backend.py --help` → `rc=0` | Names no interpreter. On the 3.9.6 suite interpreter it is **rc=1** — pre-existing PEP-604 `dict \| None` at `:189`, which the chunk-2 judge explicitly tolerates via a `version_info` branch. rc=0 requires 3.10+. |
| Same table: "zero `phase-*` dirs on disk" | `kimi-k3` correctly falsified this at review time (untracked `phase-4.5/` scratch residue, 11 files, mtimes predating the build commit — `git mv` leftovers, not a live-path bug). **No longer reproduces**: nothing matches `phase-*` on disk now, tracked count 0. The §4.2 gate checks `git ls-files` only, so the gate was honestly green either way. |
| Preamble: "six items, everything §2.1–§2.4 did not enumerate" | Seventh exists: `tools/sprint_loop/backends.py:125-129` gained a five-line rationale comment. Comment-only, zero behavioural impact, visible in the commit diff, but not listed. Also: the stale-fixture note scopes to `PLAN-5.1-v{5,6}.md`; `v3:88,94` and `v4:109,115` carry the same `phase-4.5/KNOWN-ISSUES.md` citations. |

---

## 3. What the executor MUST do (proposed)

1. Fix each of the four scripts in §2.1 as an atomic three-part edit — read
   root, `envelope_path` write string, output root. **Do not land a
   partial fix on any single script**; §6.1 shows why.
2. Fix `tests/test_sprint_loop.py:1119-1120` per §2.2.
3. Replace the `.gitignore:79` sentence per §2.3.
4. Leave §2.4(a)/(b) to the planner. The builder does not edit specs and
   does not edit evidence bytes.
5. One commit (§18.2). Post `VALIDATE COMPLETE:` to the LEDGER. Do not
   fire reviewers, do not hold `EVIDENCE_SIGNING_KEY`, do not write under
   `evidence/phase-4.5/tokens/`.

---

## 4. Verify (§11 exit checks) — run them, don't assert them

### 4.1 Full suite green
`python3 -m pytest -q` → **197 passed, 3 skipped**, unchanged. §2.2 changes
a fixture that currently passes, so the count must not move.

### 4.2 All four scripts exit 0 — the check chunk 2 lacked
```
python3 tools/phase-3-gen/gen-telemetry.py            ; echo rc=$?
python3 tools/phase-3.1-gen/gen-telemetry.py          ; echo rc=$?
python3 tools/phase-4-gen/reconstruct-telemetry.py --dry-run ; echo rc=$?
python3 tools/phase-4-gen/gen-findings.py             ; echo rc=$?
```
All four must be `rc=0`. Capture stdout to the chunk's evidence dir. **Run
each from a non-root CWD as well** — `gen-findings.py` is CWD-relative
today, and an exit check run only from the repo root cannot distinguish
"fixed" from "happens to work here."

### 4.3 Telemetry is merged, not truncated — the §6.1 regression guard
Before/after `wc -l telemetry/runs.jsonl`, and assert
`reconstruct-telemetry.py --dry-run` reports
`Existing rows: <N>` with **N > 0**. An `Existing rows: 0` line is the
silent-green signature and must fail the gate. This check is the one that
would have caught a partial §2.1 fix; it is load-bearing, not tidying.

### 4.4 `envelope_path` strings point at real files
For every row written to `telemetry/runs.jsonl` and
`telemetry/findings.jsonl`, assert the `envelope_path` value resolves to an
existing file. This closes the read/write coupling: a fixed reader with a
stale writer passes 4.2 and fails 4.4.

### 4.5 No stray writes
`git status --porcelain` must show no new file under `tools/telemetry/`. Its
appearance means an output root was missed.

### 4.6 `.gitignore` semantics unchanged
`git check-ignore -v` on a representative reviewer envelope must report
**not ignored**, before and after. §2.3 edits a comment only; if tracking
behaviour changes, the wrong lines were touched.

---

## 5. What NOT to do (fences)

- **Do not amend `ee90061`.** The chunk-D1-2-code gate closed against that
  exact diff; amending invalidates both attestations.
- **Do not edit `tests/test_layout_paths.py` or
  `tests/test_layout_paths_chunk2.py`.** Judges are planner-authored and
  hash-locked (`cb00dfac` / `48a579f8`). Raise `BLOCKED:` instead.
- **Do not edit any evidence byte** (§5): `FINDINGS-chunk-D1-2.md`,
  committed envelopes, manifests, raw/stream files. §2.4(b) is errata, not
  an edit.
- **Do not touch `planning/PATH-REDIRECTS.md` or living-doc citations** —
  chunk 3's surface, still fenced.
- **Do not widen into the deferred docstring/comment class.** See §7.1.
- **Do not add a `.gitignore` pattern.** §2.3 changes prose only.

---

## 6. Findings the builder raises against the review round

Recorded because the gate is closed and these adjust what the reviewers
concluded. Two corrections and one addition.

### 6.1 ADDITION — the real silent-green, missed by both reviewers

Both reviewers stopped at the read path. Neither examined the **output**
paths, and that is where the §7 defect actually is.

`reconstruct-telemetry.py:157` guards its merge with
`if os.path.exists(RUNS_PATH)`. Post-move `RUNS_PATH` is
`tools/telemetry/runs.jsonl`, which does not exist, so the guard is False,
`existing_rows` is `[]`, `:193` `merged = existing_rows + new_rows` keeps
only new rows, and `:211` opens that path `"w"`.

**Consequence: applying minimax's recommended fix in isolation converts a
loud failure into a silent one.** Repair `PHASE2_EVID`/`PHASE3_EVID` but
leave `REPO_ROOT` at `:29`, and the script gets past the `FileNotFoundError`
at `:104`, silently reads zero existing rows, writes a truncated file to a
path nothing reads, prints `Wrote N rows`, and exits **0**. The genuine
telemetry SoR at the repo-root `telemetry/runs.jsonl` is left untouched, so
nothing is destroyed — but the operator is told the reconstruction
succeeded when it silently dropped every pre-existing row. OPERATING-RULES
§7 and §10.

This is why §2.1 is structured per-script and §4.3 exists.

### 6.2 CORRECTION — `minimax-m3` mis-framed the current failure as silent-green

minimax reported `reconstruct-telemetry.py --dry-run` as exiting **0**
despite the `FileNotFoundError`, citing §7/§10. Measured: **rc=1**. All
four scripts fail closed today, which is the *correct* §7 failure mode.
That does not make them non-defects — four scripts cannot be re-run — but
it lowers severity from "corrupting the telemetry SoR" to "loudly broken,"
and it relocates the real silent-green to §6.1, which minimax did not find.

### 6.3 CORRECTION — regression vs. pre-existing rot, established not assumed

Neither reviewer checked the predecessor. Both frame the four scripts as
"pre-move paths were valid," which is inference from the layout rather than
measurement. Measured in a throwaway worktree at `c63b776`:

| Script (pre-move path) | `c63b776` | `ee90061` |
|---|---|---|
| `phase-3/gen-telemetry.py` | **rc=0** | rc=1 `FileNotFoundError` |
| `phase-3.1/gen-telemetry.py` | **rc=0** | rc=1 `FileNotFoundError` |
| `phase-4/reconstruct-telemetry.py --dry-run` | **rc=0** | rc=1 `FileNotFoundError` |
| `phase-4/gen-findings.py` | **rc=0** | rc=1 `FileNotFoundError` |

All four are chunk-2 regressions, not inherited breakage. This matters for
whether the chunk is defensible: chunk 2 broke working scripts, and 2a
repairs them. Reproduction commands belong in 2a's evidence dir.

### 6.4 `kimi-k3` finding confirmed as no longer reproducing

Recorded in §2.4(b) so the erratum is accurate as of `3a6b76f` rather than
as of review time.

### 6.5 GAP in `CHUNK-2a-SPEC.md` §4 — no exit check catches the partial fix

The spec's §2.1 states each script has **two** independent defects (read path,
`envelope_path` write string). There is a **third** — the output root — and
while the spec's bullets do list it (`gen-telemetry.py:23` `OUT`,
`phase-3.1/gen-telemetry.py:22` `RUNS`), its §4 exit criteria contain nothing
that would detect it being missed.

The consequence is specific and matches §6.1. `CHUNK-2a-SPEC.md` §4.2 is
"all four scripts rc=0 invoked from a non-root CWD." A `reconstruct-telemetry.py`
whose `:31-32` read paths are repaired but whose `:29` `REPO_ROOT` is not:

- exits **0** → passes spec §4.2
- emits no `^phase-\d` `envelope_path` → passes spec §3 judge assertion 2
- silently reads `Existing rows: 0` at `:157`, keeps only new rows at `:193`,
  and truncating-writes to `tools/telemetry/runs.jsonl` at `:211`

So the chunk closes green on a script that silently discarded every
pre-existing telemetry row. **Asserting rc=0 is asserting on an exit code** —
the §7 failure mode the framework exists to prevent, reproduced inside the
spec written to fix a §7 failure.

Requested additions to spec §4 (this draft's §4.3 and §4.5):
1. `reconstruct-telemetry.py --dry-run` must report `Existing rows: N` with
   **N > 0**; `Existing rows: 0` fails the gate.
2. `git status --porcelain` must show no new file under `tools/telemetry/`.
3. Every `envelope_path` emitted must resolve to a file that exists — shape
   assertion 2 in spec §3 checks the prefix is *not* stale, not that the
   target is *real*.

### 6.6 `CHUNK-2a-SPEC.md` §6's rename-count correction is itself false

Spec §6 instructs: *"Report rename counts exactly: chunk-D1-2's row claimed
'618 all R100' where the truth was 617 R100 + 1 R089."*

**Measured — the original claim was correct and the correction is not:**

```
git diff-tree -r -M --no-commit-id ee90061^ ee90061 | awk '{print $5}' | sort | uniq -c
    618 R100
     16 M
git diff-tree -r -M --no-commit-id ee90061^ ee90061 | awk '$5 ~ /^R/ && $5 != "R100"'
    (empty)
```

No `R089` exists in `ee90061`. Nor anywhere on the branch: scanning every
commit in `c63b776..HEAD` for non-`R100` rename statuses returns zero. The
adjacent commits are not the source either — `bc83471` is `5 A + 1 M`,
`745a786` is `7 A + 1 M`, `3a6b76f` is `1 M`, `82df5bf` is `2 A + 1 M`. None
contain a rename at all, so the "builder's own row landed in the same range"
explanation does not hold: the builder's LEDGER row is in `bc83471`, a
separate commit with no renames in it.

Both reviewers independently reached 618 R100 by different instruments
(`git show --name-status` and `git diff-tree -r -M`), which is three
independent measurements against one unsourced correction.

This needs fixing before the spec locks, and not only for tidiness. As
written, spec §6 directs the executor to record `617 R100 + 1 R089` in the
chunk's evidence — a falsifiable error introduced *by* the instruction whose
stated rationale is that "a reviewer who checks it starts discounting
everything around it." A reviewer will check it, and it will not hold.

Recommend deleting the parenthetical correction and keeping the instruction:
"report rename counts exactly, from `git diff-tree -r -M`, and name the
instrument." If the planner has a measurement I could not reproduce, I'd want
the exact command — I may be using a different rename-detection threshold, and
`-C` copy detection or a non-default `-M<n>%` could plausibly reclassify one
pair.

---

## 7. Open questions for the planner

### 7.1 The deferred docstring / CI-comment class still has no owner
Both reviewers flagged this and it is **out of scope above** — flagged, not
resolved. Stale old-layout citations survive in `.py` docstrings
(`sign_chunk_token.py:6,135`, `per_chunk.py`, `local_backend.py:6`,
`sprint_loop/__init__.py`, moved scripts' docstrings) and in
`.github/workflows/adversarial-sprint-ci.yml:24,85,126` (citing
`phase-4.5/CI-GATE.md`, `phase-4.5/KNOWN-ISSUES.md`). `CHUNK-3-SPEC` §2.1
is markdown-only, so nothing owns them. Three options: extend chunk 3's
allowlist to `.py` docstrings + CI comments; add them to 2a; or record them
as explicit post-D1 follow-ons. I have no strong preference — they are
inert prose — but §5's escape valve requires they be *recorded* somewhere,
and right now the fence points at a chunk that does not own the surface.

### 7.2 chunk-D1-1's post-verdict nits — still unanswered
The scope approved above does not mention them, so I have **not** folded
them in. They remain where they were: unresolved as in-chunk vs. follow-on,
against commit `5cd2ac4`, envelopes under
`evidence/phase-4.5/build-evidence/r-chunk1-code-r3-20260814-0141/`. If 2a
should absorb them, say so and I will revise this draft; I did not want to
silently widen an approved scope.

### 7.3 Bootstrap vs. literal prefix in §2.1
Recommendation stated (bootstrap through `sprint_loop.config`), tradeoff
named (four new `sys.path` bootstraps vs. four new hardcoded prefixes that
re-break on the next move). Planner's call; either is implementable as
specced.

---

## 8. Chunk-close protocol (unchanged, restated for completeness)

Builder builds, verifies, commits, pushes to `dev`, posts
`VALIDATE COMPLETE:` and stops. Builder does not fire `droid exec` against
reviewer models, does not hold `EVIDENCE_SIGNING_KEY`, does not write
`evidence/phase-4.5/tokens/chunk-D1-2a.token.json`. Two ACCEPT-class
verdicts from distinct families close the gate; the referee signs (§21–§24).

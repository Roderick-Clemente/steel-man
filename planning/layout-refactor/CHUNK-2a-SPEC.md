# CHUNK-D1-2a — operational-code path repair (follow-on to chunk-D1-2)

**Predecessor:** chunk-D1-2, gate CLOSED on build commit `ee90061`
(kimi-k3 + minimax-m3, both ACCEPT-WITH-NITS). Token signed by the referee
at `82df5bf`, key id `referee-deepseek-2026-08-14`.

**Successor gate:** `tools/chunk_sequence_gate.py --prior-token
evidence/phase-4.5/tokens/chunk-D1-2.token.json --next-chunk-id chunk-D1-2a`
— signature-only. Do **not** pass `--check-current-head`: the token binds
`ee90061` and HEAD has legitimately advanced past it. The gate is run by
the referee, which holds `EVIDENCE_SIGNING_KEY`; the builder cannot run it
and must not be asked to (§22).

**Why this chunk exists.** chunk-D1-2 moved 617 files and closed cleanly, but
its reviewers surfaced four live scripts that the moves broke. They cannot be
absorbed into chunk-D1-2 — §18.2 is one chunk, one commit, and amending it
would invalidate the diff both reviewers attested to. They also cannot land in
chunk-D1-3: that chunk's §2.1 allowlist is markdown-only and its §4.2 grep is
`--include='*.md'`. Four `.py` files in a markdown-only sweep is a category
error. Chunk 3 keeps its value by staying mechanical and greppable.

These are **regressions, not pre-existing rot** — established by the builder
running each script against the predecessor commit:

| script | `c63b776` (pre-move) | `ee90061` (post-move) |
|---|---|---|
| `tools/phase-3-gen/gen-telemetry.py` | rc=0 | rc=1 `FileNotFoundError` |
| `tools/phase-3.1-gen/gen-telemetry.py` | rc=0 | rc=1 `FileNotFoundError` |
| `tools/phase-4-gen/reconstruct-telemetry.py` | rc=0 | rc=1 `FileNotFoundError` |
| `tools/phase-4-gen/gen-findings.py` | rc=0 | rc=1 `FileNotFoundError` |

All four fail closed, which is the correct §7 behaviour — nothing downstream
has silently recorded bad data. That lowers urgency from "corrupting the
telemetry SoR" to "four scripts nobody can re-run." It does not make them
non-defects.

---

## §2.1 — The four scripts: read path and write string move together

Each script has **two** independent defects, and fixing only the first
converts a loud failure into poisoned telemetry. **They must be fixed in the
same commit.** A read-path fix without the corresponding `envelope_path` fix
is a regression of a worse kind than the one it repairs.

Route all path resolution through the constants established by chunks 1–2 in
`tools/sprint_loop/config.py` — `EVIDENCE_ROOT`, `BUILD_EVIDENCE_REL`,
`BUILD_EVIDENCE_DIR`, and the `phase_path(framework_root, kind, *parts)`
accessor at `config.py:117`. Do not re-hardcode the new literal prefix; that
is the same over-fitting that made these four break.

**A. `tools/phase-3-gen/gen-telemetry.py`**
- `:22` `EVID = os.path.join(os.path.dirname(__file__), "build-evidence")`
  — self-relative. The script used to sit beside its evidence; it now lives
  under `tools/` and the sibling is gone.
- `:23` `OUT = os.path.join(os.path.dirname(__file__), os.pardir, "telemetry", "runs.jsonl")`
  — same class.
- `:101` `"envelope_path": "phase-3/build-evidence/" + fname` — dead prefix
  written into every new telemetry row.

**B. `tools/phase-3.1-gen/gen-telemetry.py`**
- `:21` `EVID`, `:22` `RUNS` — self-relative, as above.
- `:106` `"envelope_path": "phase-3.1/build-evidence/" + fname` — dead prefix.

**C. `tools/phase-4-gen/reconstruct-telemetry.py`**
- `:29` `REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), os.pardir))`
  — **this is the precise bug.** Two levels up from
  `tools/phase-4-gen/reconstruct-telemetry.py` resolves to `tools/`, not the
  repo root. The script assumed it sat one level below root. From
  `tools/phase-*-gen/` the framework root is three `dirname` calls up; see
  `config.py:24` for the established idiom.
- `:31-32` `PHASE2_EVID`, `PHASE3_EVID` — derived from the wrong `REPO_ROOT`.
- `:172`, `:180` `env_rel = f"phase-2/build-evidence/{fname}"` and the
  `phase-3` equivalent — dead prefixes reaching `:137`'s `envelope_path`.

**D. `tools/phase-4-gen/gen-findings.py`**
- `:153`, `:190` `open("phase-3.2/reviews/…json")` — CWD-relative. Worked only
  when invoked from the repo root and the directory existed there.
- `:235`, `:271` `open(f"phase-4/post-v3-review-{name}-envelope.json")` and
  `f"phase-4/track-execution-review-{name}-envelope.json"` — same class.

**Existing rows in `telemetry/runs.jsonl` are NOT rewritten.** They are
historical evidence under §5/§21 and their old-prefix `envelope_path` values
are accurate records of where those bytes lived at the time. The dead-pointer
delta is carried by `planning/PATH-REDIRECTS.md` per `PLAN.md:497`. Only
newly-generated rows use resolved paths.

## §2.2 — Stale test fixture

`tests/test_sprint_loop.py:1119-1120` — `mkdirs` on `"fw"/"phase-1"/"scripts"`
and `"fw"/"phase-3.2"/"evidence"`. The test passes because `_validate_config`
only requires `tools/sprint_loop`, so these create directories nothing reads.
Silent-green flavoured, and outside `ROUTED_PY_FILES`, so no judge catches it.
Point them at the taxonomy homes: `SCRIPTS_ROOT` (`tools/phase-1-scripts`) and
`EVIDENCE_CODE_ROOT` (`tools/phase-3.2-evidence`).

This was found by kimi-k3 as a third site where the builder's Finding 5
enumerated two. The enumeration gap is itself worth noting in the evidence.

## §2.3 — Tighten `.gitignore:79`

The prose claim "cannot be undone with a `!` negation" is too broad and must
narrow to what was actually tested:

- A **file-level** `!` inside a directory-form exclude does **not** re-include.
  This is the classic gotcha, and it is the form minimax-m3 proposed — so
  minimax's nit is correct but its example is backwards.
- A **directory-level** negation (`!evidence/phase-4.5/build-evidence/r-<id>/`)
  **does** re-include.

The chunk-D1-2 refusal still stands, on minimax's own reasoning rather than
the builder's: re-inclusion requires enumerating each run-id directory at
creation time, which is the unmaintainable shape. Keep the refusal, fix the
justification. **Do not add the `evidence/*/build-evidence/r-*/` keep-pattern**
— the prefix-form exclude removed on 2026-08-13 silently dropped the
chunk-D1-1-spec envelopes that a signed referee token attested to, and adding
the variant reinstates that exact shape.

## §2.4 — Errata pass (append-only)

These target `FINDINGS-chunk-D1-2.md`, a committed evidence byte. **Correct
them by appending errata rows, never by editing the file** (§5, §21).

- **K2 stands.** The `local_backend.py --help | rc=0` row names no interpreter.
  On the 3.9.6 suite interpreter it is rc=1 — pre-existing PEP-604
  `dict | None` at `:189`, which the chunk-2 judge explicitly tolerates. rc=0
  requires 3.10+. Record the interpreter, not just the code.
- **K5 stands.** `backends.py:125-129` gained a comment block inside a set of
  six changes presented as unenumerated. Comment-only, zero behaviour.
- **K1 does not reproduce.** kimi flagged untracked `phase-4.5/` scratch
  residue contradicting the "zero `phase-*` dirs on disk" row. Accurate at
  review time, moot now: nothing matches `phase-*` on disk, tracked count 0.
  Record as time-of-review divergence, not as a defect.
- **No change needed:** minimax's lookbehind item (the fix was right; it asks
  only that the comment survive chunk 3's rename) and its §2.4
  `verify-green.py` line-number errata, which corrects a spec, not a build.
- **New — `provider` is empty in both signed tokens.** Every reviewer record
  in `chunk-D1-1.token.json` and `chunk-D1-2.token.json` carries
  `"provider":""`. Nothing currently breaks: Ruling 2c fixes seat identity by
  `model_id`, and `family` is populated, so §17.2 cross-family and §23
  paraphrase both still resolve. But the tokens are HMAC-signed and therefore
  immutable — if any future gate ever asserts `provider` non-empty, these two
  retroactively fail and cannot be repaired. **The fix is forward-only:**
  populate `provider` on all subsequent tokens; record these two as a known
  incompleteness. Do **not** re-sign — re-signing an immutable token to make a
  record look tidier is the exact move the signing scheme exists to prevent.

---

## §3 — Judge

The judge for this chunk is **drafted by the planner and its content hash
ratified by the referee before it locks.** The builder does not author or
modify it (invariant 3), and planner-drafted judges no longer lock unreviewed
now that planner and builder share a model family.

It must assert **behaviour, not literals** — the failure that produced this
chunk was a judge tied to Chunk-1's literal constant values. Required
assertions:

1. Each of the four scripts exits 0 when invoked from a directory that is
   **not** the repo root. CWD-independence is the actual invariant; asserting
   it from the repo root only would pass vacuously for `gen-findings.py`.
2. No `envelope_path` value emitted by any of the four matches
   `^phase-\d`, **and** each emitted path resolves to an existing file.
   Shape alone is insufficient — see §4.7; a partial fix satisfies the
   regex while pointing at nothing.
3. `tests/test_sprint_loop.py`'s fixture directories resolve under
   `SCRIPTS_ROOT` / `EVIDENCE_CODE_ROOT` rather than bare `phase-*` segments.

## §4 — Exit criteria (run and reported, not asserted — §11)

1. Full suite green on the 3.9.6 suite interpreter; report passed/skipped
   counts and the interpreter version explicitly (§2.4 K2 is why).
2. All four scripts rc=0 invoked from a non-root CWD, with output shown.
3. `grep -rn 'phase-[0-9]' ` over the four scripts returns no path-forming
   occurrence; prose and docstring mentions are acceptable and should be
   listed rather than silently kept.
4. Both existing judges byte-unchanged (`cb00dfac`, `48a579f8`) and matching
   their locks under `tools/phase-1-locks/tests/`.
5. `tools/plan-lint.py` rc=0.
6. Diff contains **no** rename of any file under `evidence/` — this chunk
   moves nothing. Any `R` status line in the diff is a scope escape.

7. **Artifact-level checks — criteria 1–3 cannot detect a partial fix**
   (builder finding 6.5 — upheld, and it invalidates the draft's §3
   assertion 2 as sufficient). Repairing
   `reconstruct-telemetry.py:31-32` without `:29` leaves
   `REPO_ROOT` at `tools/`, so `RUNS_PATH` becomes
   `tools/telemetry/runs.jsonl`. The script then exits 0 and emits no stale
   `envelope_path` — passing criteria 2 and 3 — while `:157`'s
   `if os.path.exists(RUNS_PATH)` guard silently reads **zero** existing
   rows and `:211`'s `open(RUNS_PATH, "w")` truncating-writes a forked
   telemetry file. rc=0, judge green, system of record split in two. Per §7,
   asserting rc=0 is asserting on an exit code, not on evidence. Therefore
   also verify:
   - `telemetry/runs.jsonl` row count **before** the run is > 0 and the
     count after is `>=` the count before. A merge that shrinks the SoR is
     a failure, not a nit.
   - `git status --porcelain` and a filesystem check show **nothing written
     under `tools/telemetry/`** — that directory must not come into
     existence.
   - Every `envelope_path` emitted resolves to a file that actually exists
     on disk. Shape-matching a resolved path is necessary but not
     sufficient; a well-formed pointer to nothing is the defect this chunk
     exists to prevent.

## §5 — Forbidden

- Do not amend, revert, or force-push `ee90061` or any commit at or before it.
  Append-only, always, on a branch three other seats work.
- Do not edit `tests/test_layout_paths.py` or `tests/test_layout_paths_chunk2.py`.
- Do not edit existing `LEDGER.md` rows or `FINDINGS-chunk-D1-2.md`.
- Do not write under `evidence/phase-4.5/tokens/`, hold `EVIDENCE_SIGNING_KEY`,
  or fire `droid exec` against any reviewer model (§22).
- Do not widen scope into chunk-D1-3's markdown surface.

## §6 — Evidence to commit

Per-seat commit trailer required.

**Errata against this spec's own first draft (builder finding 6.6 — upheld).**
The draft asserted chunk-D1-2's "618 all R100" was really "617 R100 + 1 R089."
That is wrong. `git show --name-status ee90061` is **618 R100 + 16 M**, zero
non-R100 renames, and no `R089` appears in any commit in `c63b776..HEAD`. The
builder's original count was correct and the planner's correction was the
falsifiable claim. Recorded here rather than quietly deleted, because a spec
that lectures about unverified counts while carrying one is worth less than the
correction. The underlying instruction stands on its own: **report rename
counts from `--name-status` output, and quote the command.**

Carry the predecessor-commit reproductions (`c63b776` vs `ee90061`) into the
evidence bundle. Establishing these as regressions rather than pre-existing
rot is what makes the chunk defensible, and it is the part neither reviewer
did.

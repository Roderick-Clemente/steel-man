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

**Why this chunk exists.** chunk-D1-2 moved 618 files (`--name-status`: 618 R100 + 16 M, see §6) and closed cleanly, but
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
delta is carried by `planning/PATH-REDIRECTS.md` per `PLAN.md:465` and `:639`. Only
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

## §2.5 — Fifth script: `lock.py`'s default `--locks-dir`

Found while preparing the referee's ratification step, and it is the same
defect class as the four:

`tools/phase-1-scripts/lock.py:42` defaults `--locks-dir` to
`os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "locks")`.
Pre-move that resolved `phase-1/scripts/lock.py` → `phase-1/locks` correctly.
Post-move it resolves to **`tools/locks`**, which does not exist. The real
locks are at `tools/phase-1-locks/tests/`. `LOCKS_ROOT` already holds the right
value in `config.py`; the script simply does not use it.

This one is worse than the other four, because it does not fail closed. The
other four raise `FileNotFoundError`. `lock.py` would write a lock manifest to
a fresh wrong directory and report success — and the judge-immutability
enforcement that reads locks from the real location would then be silently
unenforced while every log line says the test is locked. Invariant 3 would be
off, with no signal. That is the exact silent-success shape §7 exists to
forbid.

It escaped the chunk-2 residual scan because `tools/phase-1-scripts/lock.py`
is not in the chunk-2 judge's `ROUTED_PY_FILES`. **Add it**, along with
`tools/phase-1-hooks/locked-test-guard.py`, in the 2a judge's own routed set —
a lock writer and a lock reader that disagree about where locks live is the
worst pair in the repo to leave unrouted.

Also stale, and harmless, but fix while here: `tools/sprint_loop/per_chunk.py:136`
comments that "lock.py writes to `phase-1/locks/<test_file>.lock.json`." It is
a comment, so the AST-based residual scan cannot see it.

**Referee workaround, so ratification is not blocked behind this fix:** pass
`--locks-dir tools/phase-1-locks` explicitly. With
`test_file = tests/test_layout_paths_chunk2a.py` that composes to
`tools/phase-1-locks/tests/test_layout_paths_chunk2a.py.lock.json`, matching
the two existing manifests exactly. No code change needed to lock the 2a judge.

## §2.4 — Errata pass (append-only)

These concern `FINDINGS-chunk-D1-2.md`, a committed evidence byte. It is
immutable under §5/§21, so **record them as appended LEDGER rows naming what
each supersedes — do not touch the findings file.**

**Closed.** The builder appended all four as `ERRATUM: supersedes=…` rows at
`planning/phase-4.5/LEDGER.md:904-957`, zero deletions. kimi-k3 filed a
`medium` saying they were never recorded anywhere durable; that finding **does
not reproduce** — it grepped `"K2 stands"` and the rows read `K2 STANDS`, a
case-sensitivity miss. Verified present and append-only.

**Erratum against this instruction's own first draft.** It read "correct them
by appending errata rows, never by editing the file," which cannot be
followed: appending to a file *is* editing it, and §5/§21 forbid editing that
file at all. The instruction named no legal destination, so it was impossible
as written. The builder correctly recorded nothing rather than violate
immutability, and kimi-k3 then filed the absence as a blocker — the builder
was right about the artifact, kimi was right about the gap, and the spec was
the thing at fault. The LEDGER is the append-only errata record; that is
where these belong.

- **K2 stands, with the label corrected.** The `local_backend.py --help | rc=0`
  row names no interpreter, and it should. Measured both ways:
  `/private/tmp/asprint-venv/bin/python` (3.13.3) gives **rc=0**;
  `/usr/bin/python3` (3.9.6) gives **rc=1** on the pre-existing PEP-604
  `dict | None` at `:189`, which the chunk-2 judge explicitly tolerates.
  3.9.6 is the **system** interpreter, not the suite interpreter — the suite
  runs on the 3.13.3 venv. So the original row's rc=0 was correct and only
  under-specified. Record the interpreter path, not just the code.

  **Scope correction (kimi-k3, low).** The claim "3.9.6 has no pytest
  installed at all" is true on the builder's machine and was stated
  absolutely. On kimi's machine `/usr/bin/python3` has pytest 8.4.2 and runs
  the suite, and the repo's own lock manifests attest "197 passed + 3
  skipped on Python 3.9.6" — so as written it contradicts a committed
  artifact. Interpreter availability is machine-scoped; say which machine.
- **K5 stands.** `backends.py:125-129` gained a comment block inside a set of
  six changes presented as unenumerated. Comment-only, zero behaviour.
- **K1 does not reproduce.** kimi flagged untracked `phase-4.5/` scratch
  residue contradicting the "zero `phase-*` dirs on disk" row. Accurate at
  review time, moot on the builder's machine at build time: nothing matched
  `phase-*` on disk there, tracked count 0. Record as time-of-review
  divergence, not as a defect — and machine-scoped, since kimi-k3 found
  untracked `phase-4.5/` scratch present on its own checkout. The gate
  point (`git ls-files` count 0) is unaffected either way.
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
   `^phase-\d`. Shape alone is insufficient — a partial fix satisfies the
   regex while pointing at nothing — so resolution is **also** required, but
   it is enforced at the §4.7 exit-criteria level rather than here.

   **Erratum superseded — the resolution half IS enforceable, and is now
   enforced.** A prior erratum here claimed a side-effect-free judge
   "structurally cannot" observe emitted values, because observing them
   means running the writers and running them mutates the SoR. That was
   wrong, and it was the most expensive thing in this spec: it argued a real
   requirement out of existence, and kimi-k3 then walked straight through
   the gap it left (blocker 1 — a fix emitting `build-evidence/<file>`,
   which carries no `phase-N` prefix, resolves to nothing, and was
   demonstrated 16/16 green against the ratified judge).

   It is the **write** that must not happen, not the run. The amended judge
   replaces `builtins.open` so write modes return an in-memory sink, then
   executes each generator for real from a temp CWD: every byte it would
   have written is captured and parsed, and every newly-generated
   `envelope_path` is asserted to resolve. Verified safe against all four
   subjects — each performs every read before its first write, and none
   calls `os.makedirs`, `os.replace`, or `shutil`, so no write escapes the
   intercept.

   Two scoping facts the assertion must respect, both learned by measuring:
   `reconstruct-telemetry.py` emits 39 rows, of which 21 are **carried
   through** from the existing SoR — their old-prefix values are accurate
   §5/§21 records (one points into a different pilot repo entirely) and are
   out of scope per §2.1. Only the 18 generated rows are this chunk's
   responsibility, which is exactly the 18/18 the builder reported. The
   judge separates the two by excluding values already present in the SoR.
3. `tests/test_sprint_loop.py`'s fixture directories resolve under
   `SCRIPTS_ROOT` / `EVIDENCE_CODE_ROOT` rather than bare `phase-*` segments.

## §4 — Exit criteria (run and reported, not asserted — §11)

1. Full suite green on the suite interpreter. Pre-2a baseline is
   **197 passed + 3 skipped**. The 2a judge was 16 tests; the ratified
   amendment (below) takes it to **23**, so the 2a contribution is 23, not
   16. Measured valid RED before any fix was **12 failed, 201 passed, 3
   skipped** against the 16-test judge.

   **Gate on the 2a judge in isolation — `pytest -q
   tests/test_layout_paths_chunk2a.py` must be 23 passed.** The full-suite
   number at the branch tip also contains the chunk-D1-3 judge (14 tests,
   10 of them a deliberate valid RED until chunk 3 is built), so a bare
   full-suite count is not a pass/fail signal for this chunk. Report both,
   plus the interpreter path — §2.4 K2 exists because a bare rc was recorded
   without one.

   **Interpreter caveat, and it is a real defect in this pin.** The path
   `/private/tmp/asprint-venv/bin/python` is under `/tmp` and does not
   survive across machines or reboots; kimi-k3 found it absent and
   substituted its own venv. A suite interpreter that cannot be
   reconstructed from the repo is not a reproducible pin. Filed as a
   follow-on: the pin needs a repo-local or documented-bootstrap path.
   Until then, reviewers state the interpreter they built and its version.
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

   **Errata, filed post-build against the planner — "system of record" is
   overstated.** This spec calls `telemetry/runs.jsonl` the SoR in §2.1 and
   above. It is **gitignored** (`.gitignore:44`) and therefore not a
   committed artifact. Two consequences a reviewer should not mistake for a
   contradiction:

   - The row-count check measures a working-tree file. On a fresh clone
     `telemetry/runs.jsonl` does not exist at all, so that check is
     unrunnable there and its absence is not a finding. Run it in a tree
     that has one, or state that you could not.
   - The defect is undiminished. A forked write to `tools/telemetry/` still
     splits the file on every local run, and the `envelope_path` values
     landing in it must still resolve. What changes is the stake: this is a
     local generated artifact, not evidence, so "poisoned telemetry" means
     a broken local tool rather than a corrupted audit trail.

   The planner ran the three writers without `--dry-run` while verifying the
   build, which the reviewer rules forbid. It was idempotent — the merge is
   keyed on `run_id`, 21 rows before and after — but it should not have been
   done, and it is recorded here rather than omitted.

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

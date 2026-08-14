# CHUNK-D1-3 — living-doc citations, `planning/PATH-REDIRECTS.md`, LEDGER rename

**Parent PLAN:** `planning/layout-refactor/PLAN.md` (`4caac15`)
**Branch:** `factory/layout-refactor` in
`git@github.com:Roderick-Clemente/adversarial-sprint-dev.git`
**Chunk ID:** `chunk-D1-3`
**Predecessor:** `chunk-D1-2a` — build commit `da14ef5`

**Predecessor gate (BLOCKING — chunk 3 does not open until this passes):**

```
tools/chunk_sequence_gate.py \
  --prior-token evidence/phase-4.5/tokens/chunk-D1-2a.token.json \
  --next-chunk-id chunk-D1-3
```

Signature-only. Do **not** pass `--check-current-head`: the token binds
`da14ef5` and HEAD has legitimately advanced past it (`08d0072`, `0b1262c`).
The gate is run by the referee, which holds `EVIDENCE_SIGNING_KEY`; the
builder cannot run it and must not be asked to (§22). At the time this spec
was written the chunk-D1-2a token did **not yet exist** — kimi-k3 and
minimax-m3 were still in flight against `da14ef5`. This spec is drafted
ahead of that gate deliberately, so planner work is not the critical path;
it confers no permission to start.

**Successor gate (for whoever opens chunk-D1-4):**

```
tools/chunk_sequence_gate.py \
  --prior-token evidence/phase-4.5/tokens/chunk-D1-3.token.json \
  --next-chunk-id chunk-D1-4
```

---

## §1 — Problem statement (§13)

Chunk 2 moved 618 tracked files out of the `phase-N/` silos. Markdown
citations of the old paths were deliberately fenced to this chunk. Living
docs get updated to the new `evidence/`, `planning/`, `tools/phase-N-*/`
homes; **evidence bytes are immutable** (§5, §21), so citations inside
committed envelopes, manifests, and raw/stream files stay as they are and
are covered by a redirects file. This chunk also moves the LEDGER to its
correct home.

**The parent PLAN's "~150 citations" is wrong, and the correction changes
the shape of the chunk.** Measured on `0b1262c` across the full allowlist:

| surface | files | bare `phase-N/` path tokens |
|---|---|---|
| **§2.1a citation-edit surface** | 27 (15 with hits) | **105** |
| `planning/layout-refactor/**` | 8 | 265 |
| `planning/phase-N/**` | 55 | 418 |
| **allowlist total** | **90** | **788** |

788 rewrites in one chunk would blow the §17 capacity envelope outright. It
is also the wrong thing to do: **683 of the 788 must not be edited at all**,
for reasons specific to each bucket (§2.1b). The chunk stays inside its
envelope by editing 105 tokens and *redirecting* the other 683 — which was
always the intent of the §5 hard stop, just never measured.

---

## §2 — Surface touched

### §2.1a — Citation-edit surface (the allowlist, bounded per §17)

The executor updates path citations in EXACTLY these files and no others. A
file not on this list that surfaces a citation is NOT in scope for D1 —
record it as a follow-on.

| file | baseline bare `phase-N/` tokens |
|---|---|
| `droid-wiki/by-the-numbers.md` | 33 |
| `droid-wiki/lore.md` | 16 |
| `tools/OPERATING-RULES.md` | 15 |
| `PRD.md` | 9 |
| `planning/ROADMAP-REVIEW-PROMPT.md` | 7 |
| `planning/ROADMAP-REVIEW.md` | 5 |
| `README.md` | 5 |
| `skills/adversarial-sprint/SKILL.md` | 4 |
| `tools/sprint_loop/prompts/test-designer.md` | 3 |
| `tools/sprint_loop/prompts/validator.md` | 2 |
| `droid-wiki/security.md` | 2 |
| `tools/sprint_loop/prompts/executor.md` | 1 |
| `tools/conventions/model-discipline.md` | 1 |
| `skills/sprint-invocation/SKILL.md` | 1 |
| `AGENTS.md` | 1 |
| **total** | **105** |

On the allowlist with zero current hits — still in scope, so a citation
introduced before the chunk lands is caught: `tools/README.md`,
`tools/KNOWN-ISSUES.md`, `tools/PHASE-0.5-CLOSE.md`, `tools/RUN-LEDGER.md`,
`tools/REPRODUCE.md`, the remaining `tools/conventions/*.md` (3), the
remaining `tools/sprint_loop/prompts/*.md` (2), `droid-wiki/*.md` (2).

`droid-wiki/` is **path tokens only.** Content freshness is D3, not D1. Do
not rewrite wiki prose.

### §2.1b — Redirect-only surface (in the allowlist, NOT citation-edited)

The parent PLAN widened the allowlist to "all docs moved into
`planning/<phase>/`". Taken literally that pulls in 683 tokens whose edits
would range from meaningless to destructive. Both buckets are handled by
`planning/PATH-REDIRECTS.md` instead, and this is the §5 hard stop firing
as designed rather than a scope reduction.

**`planning/layout-refactor/**` — 265 tokens. These are the specs that
describe this very move.** Their `phase-N/` tokens are the *before* side of
move tables. `CHUNK-2-SPEC.md:29` reads:

```
- `phase-0/evidence/` → `evidence/phase-0/`
```

"Updating the citation" yields `evidence/phase-0/` → `evidence/phase-0/`,
which destroys the document's meaning. `PLAN.md`'s tokens are diagnostic
narrative of the same kind (`:15` "`phase-1/locks/`" naming what was
misclassified). A document whose subject is a rename cannot have its
old-path references rewritten. **Zero edits here.**

**`planning/phase-N/**` — 418 tokens. Time-stamped historical run
records.** RUN-PROMPTs, KICKOFFs, RUN-COMMANDS, BUILD-NOTES, postmortems.
`planning/phase-3/RUN-COMMANDS.md:22` records the literal command that was
executed at the time (`-f phase-3/prompts/chunk1-test-author.md`). Rewriting
it produces a command that was never run — falsifying a record to fix a
link. This is exactly the §2.3 historical-narrative case, at scale.
**Zero edits here**; covered by prefix entries in PATH-REDIRECTS.

`planning/phase-4.5/LEDGER.md` (61 of those 418) is additionally governed by
§2.4 — it moves, and it is append-only.

### §2.2 — `planning/PATH-REDIRECTS.md`

Create it. Table of old-prefix → new-prefix, plus the matching algorithm,
carried verbatim from `PLAN.md:445-460`:

1. strip an optional absolute repo-root prefix
   (`/Users/factory/work/adversarial-sprint-dev/`) from the cited path;
2. match the **longest** old-prefix in the table against the resulting
   relative path;
3. apply only to path-shaped tokens
   (`(?:tools|phase-\d+(?:\.\d+)?|tests|telemetry|evidence|planning)/[\w/.-]+`);
4. leave prose mentions ("Phase 1 built…") untouched.

Example, segment-preserving:

```
phase-4.5/build-evidence/ → evidence/phase-4.5/build-evidence/
```

so `phase-4.5/build-evidence/r-drs-role-split-1/envelopes/grok-4.5.raw.txt`
→ `evidence/phase-4.5/build-evidence/r-drs-role-split-1/envelopes/grok-4.5.raw.txt`.

The file must also carry, as named sections:

- **Historical-narrative exceptions** — every residual bare `phase-N/` token
  left in the §2.1a surface, enumerated file:line. §4.2 asserts against this
  list, so it cannot be hand-waved.
- **Whole-tree redirect-only surfaces** — `planning/layout-refactor/**` and
  `planning/phase-N/**` per §2.1b, with the reason. A reader who greps those
  trees and finds old paths needs to know it is intentional.
- **Lock-frozen live code** — `tests/test_layout_paths.py:571` cites
  `phase-4.5/LEDGER.md` in a **comment**. The file is a judge locked at
  `cb00dfac` and MUST NOT be touched. This is the only case where the
  redirects file covers a stale citation inside live code rather than inside
  evidence; say so explicitly.

### §2.3 — Citation update rule

For each path-shaped token in a §2.1a file:

- If the token names a `phase-N/...` path that moved, rewrite it to the new
  prefix (`evidence/phase-N/...`, `planning/phase-N/...`,
  `tools/phase-N-*/...`).
- If the token is historical narrative — "Phase 1 built
  `phase-1/scripts/lock.py`" — leave it and either add a same-line redirect
  note `(now tools/phase-1-scripts/lock.py)` **or** enumerate it in the
  PATH-REDIRECTS historical-narrative exception list. Do not rewrite
  narrative.

### §2.4 — LEDGER rename (a rename, not a citation edit)

Chunk 2 landed the ledger at `planning/phase-4.5/LEDGER.md` as a side effect
of clearing the repo root. Wrong home: it is the sprint's general-purpose
record — SHA MAP, rulings, errata, chunk closes spanning every phase — not a
phase-4.5 planning doc. It belongs at `evidence/LEDGER.md`, unpartitioned at
the evidence root for the same reason `planning/ROADMAP-REVIEW.md` sits at
the planning root.

```
git mv planning/phase-4.5/LEDGER.md evidence/LEDGER.md
```

**Rename only, zero content edits.** Verified clean: no executable code
resolves this path. The full audit finds exactly two referrers, neither
editable — the `test_layout_paths.py:571` comment (lock-frozen) and
`evidence/…/BUILDER-HANDOFF-chunk-D1-2.md:225` (immutable evidence). Both
become PATH-REDIRECTS entries.

**The rename does not freeze the ledger, and reviewers must not read it that
way.** Landing under `evidence/` puts it under §5/§21, which forbid
*rewriting existing bytes*. The ledger is append-only **by design** and
future chunks still append close rows to it. Appending is compatible with
immutability; editing or reordering existing rows is not. Rows added after
the rename are normal operation, not a violation.

### §2.5 — README: dead links and the stale Layout block

The general sweep would probably catch these, but they are the
highest-visibility broken references in the repo and are pinned rather than
left to a grep. All four back the "What the runs found" findings — the
evidence citations the README's credibility rests on — and every one 404s on
GitHub today. Verified: **`README.md` is the only file in the allowlist with
any dead relative link.** Four occurrences, three unique targets, all fixed
by a `planning/` prefix. All three destinations confirmed present on disk:

| README link (dead) | new home |
|---|---|
| `:19` `./phase-3.1/RESULTS.md` (finding 1) | `./planning/phase-3.1/RESULTS.md` |
| `:27`, `:31` `./phase-5/DESIGN-ROLE-SPLIT-AND-SIGNALS.md` (findings 3, 4) | `./planning/phase-5/DESIGN-ROLE-SPLIT-AND-SIGNALS.md` |
| `:39` `./phase-1/KNOWN-ISSUES.md` (invariant 3) | `./planning/phase-1/KNOWN-ISSUES.md` |

The `Layout` code block at `README.md:52-63` is separately stale. `:59`
still lists `phase-0 … phase-5/` as "the build record" — prose describing a
layout that no longer exists, so it needs rewriting to the taxonomy homes
rather than a prefix. A reader who follows the README's own map into
nonexistent directories is the failure this chunk exists to prevent.

Two further facts about that block, since it is being rewritten anyway:

- `:61` claims **194 tests**. Measured on `0b1262c`: **213 passed, 3
  skipped**. Fix the number in the same pass.
- `evidence/` is missing from the block entirely, despite now being a
  top-level home for the build record. Add it. Every other directory the
  block names (`tools/`, `templates/`, `skills/`, `planning/`, `pilots/`,
  `droid-wiki/`, `tests/`) was verified to still exist.

---

## §3 — Judge

Judge file: **`tests/test_layout_paths_chunk3.py`**. Drafted by the planner,
content hash ratified by the referee before it locks. The builder does not
author or modify it (invariant 3); if an assertion looks wrong it raises
`BLOCKED:` rather than editing.

It must assert **behaviour and reality, not literals** — the failure that
produced chunk-2a was a judge tied to literal constant values. Required
assertions:

1. **Zero dead relative links across the §2.1a surface.** For every
   `](target)` that is not an external URL and not a bare `#anchor`,
   resolve relative to the citing file's directory and assert the target
   exists. This is the assertion that directly encodes the defect class;
   the other checks are supporting. Report count checked alongside count
   dead. Baseline is 4 dead / 3 unique, all in `README.md` — anything other
   than 0 after the chunk means the sweep regressed a clean file.
2. **Every residual bare `phase-N/` token in the §2.1a surface is
   enumerated in the PATH-REDIRECTS historical-narrative exception list**,
   by file:line. Not "zero residuals" — narrative legitimately survives —
   but no unaccounted residual. Non-vacuous because it fails both on an
   unlisted residual and on a stale list entry.
3. **PATH-REDIRECTS is truthful, not decorative.** For every old-prefix →
   new-prefix row, assert the new prefix resolves to an existing directory
   on disk. A redirect table pointing at nothing is the same defect as the
   dead links it replaces.
4. **LEDGER rename is a rename.** `evidence/LEDGER.md` exists,
   `planning/phase-4.5/LEDGER.md` does not, and the diff reports the move
   with **zero** added or deleted lines. A non-zero line count means the
   rename smuggled a content edit into an append-only file.
5. **The three README targets in §2.5 exist**, asserted by resolving them,
   not by string-matching the table.
6. **Both existing judges byte-unchanged** — `tests/test_layout_paths.py`
   at `cb00dfac`, `tests/test_layout_paths_chunk2.py` at `48a579f8` — each
   matching its lock under `tools/phase-1-locks/tests/`.

The judge must be **side-effect free**: no writes, no subprocess that
mutates the tree.

---

## §4 — Exit criteria (run and reported, not asserted — §11)

**§4.1 — Full suite green** on the suite interpreter,
`/private/tmp/asprint-venv/bin/python` (3.13.3). **This is not
`/usr/bin/python3`**, which is 3.9.6 and has no pytest installed at all;
that confusion already produced one bad evidence row (chunk-2a §2.4 K2).
Baseline entering this chunk is **213 passed, 3 skipped**. The chunk-3 judge
adds its own tests, so report the new total explicitly rather than matching
a number written here in advance. Report the interpreter path.

**§4.2 — Residual citation grep, scoped to the §2.1a surface.**

The parent PLAN left this as `<allowlisted-living-docs>`, and the earlier
draft of this spec hardcoded whole directories. Measured, that draft's
command returns **1480 hits** — unusable as an exit check, and it sweeps the
683 tokens §2.1b explicitly excludes. Use this instead:

```sh
# The §2.1a citation-edit surface, as a file list.
ls -1 PRD.md AGENTS.md README.md \
      tools/OPERATING-RULES.md tools/README.md tools/KNOWN-ISSUES.md \
      tools/PHASE-0.5-CLOSE.md tools/RUN-LEDGER.md tools/REPRODUCE.md \
      skills/adversarial-sprint/SKILL.md skills/sprint-invocation/SKILL.md \
      tools/conventions/*.md tools/sprint_loop/prompts/*.md \
      droid-wiki/*.md planning/ROADMAP-REVIEW*.md > /tmp/citation-surface.txt

# Residual bare phase-N/ path tokens.
tr '\n' '\0' < /tmp/citation-surface.txt \
  | xargs -0 grep -onE '(^|[^/A-Za-z0-9_.-])phase-[0-9]+(\.[0-9]+)?/'
```

Baseline on `0b1262c` is **105 hits across 15 files** (§2.1a table). After
the chunk, every remaining hit must appear in the PATH-REDIRECTS
historical-narrative exception list.

Why the leading character class: `[^/A-Za-z0-9_.-]` excludes an
already-rooted `evidence/phase-3/`, so no post-filter is needed and a
correctly-updated citation cannot be double-counted. Bare `phase-3` with no
trailing separator is not path-shaped and is intentionally not matched.

**Builder hazard, hit while measuring this:** the shell here is zsh, which
does **not** word-split unquoted parameter expansions. `for f in $LIST`
over a newline-separated list silently treats the whole list as one
filename and reports **0 hits per file** — a clean, plausible, completely
false green. Use `while IFS= read -r f` or the `xargs -0` form above. Per
§7, an exit check that can report zero because it ran on nothing is worse
than no check.

**§4.3 — PATH-REDIRECTS covers evidence-internal citations.** Grep evidence
files for old prefixes and confirm each is covered by a table row:

```sh
grep -rn --include='*.json' --include='*.raw.txt' --include='*.stream.json' \
  'phase-[0-9]' evidence/
```

Evidence is immutable — the output is not a fix list, it is a coverage
checklist for the table.

**§4.4 — Zero dead relative links across the §2.1a surface**, resolved
mechanically, count checked reported alongside count dead. Do not
hand-check: a link that 404s on GitHub is exactly the class a human eye
skips. Expect **0 dead**; baseline was 4.

**§4.5 — LEDGER rename verified.** `evidence/LEDGER.md` exists,
`planning/phase-4.5/LEDGER.md` does not, `git log --follow
evidence/LEDGER.md` reaches pre-rename history, and `git show --numstat HEAD
-- evidence/LEDGER.md` reports **zero** added and deleted lines. Non-zero is
a failed chunk, not a nit.

**§4.6 — `tools/wiki-link-audit.py` rc=0** (confirmed present; measured
`61 pages · dead=0 anchor=0 absolute=0 escaping=0 skeleton=0 clean`, rc=0 on
`0b1262c`, so it is already clean entering the chunk and any non-zero is
something this chunk broke). If the audit gains a false positive from the
move, fix it under the same guard rail — through a constant, per §14, not by
hardcoding.

**This check does NOT cover the dead-link criterion, and must not be
substituted for §4.4.** `wiki-link-audit.py:24` sets `WIKI = "droid-wiki"`
and `:88` walks only that subtree. It reports `dead=0` on the very commit
where `README.md` carries four dead relative links (§2.5) — because README is
outside its scope entirely. Reading "wiki-link-audit clean" as "links are
healthy" is the silent-green shape §7 forbids: a green check that was never
looking at the thing. §4.4 exists precisely because this one stops at
`droid-wiki/`.

**§4.7 — `tools/plan-lint.py` rc=0.**

**§4.8 — Scope containment.** The only rename in the diff is
`planning/phase-4.5/LEDGER.md → evidence/LEDGER.md`. No other `R` status
line. No file under `evidence/` modified in content — the LEDGER arrives by
rename, and `--numstat` proves it. Nothing written under
`evidence/phase-4.5/tokens/` (§22).

---

## §5 — Hard stop (capacity bound, per §17)

§4.2 greps for residual citations in the §2.1a surface. If the residual hits
are only historical narrative, **STOP** — enumerate them in PATH-REDIRECTS
rather than rewriting. §2.1a is the file allowlist; a file not on it that
surfaces a citation is NOT in scope for D1 (record as follow-on).

The 683 tokens in §2.1b are the hard stop already applied, with measurements
attached. Do not "finish the job" by sweeping them.

**Do not pull D3 (wiki content freshness) into D1.** `droid-wiki/` gets
path-token updates only.

---

## §6 — Forbidden

- **Do NOT edit evidence bytes.** Everything under `evidence/` is immutable
  (§5, §21). Citations inside committed envelopes stay as-is;
  PATH-REDIRECTS carries the delta. The one permitted `evidence/` operation
  is the LEDGER arriving by `git mv`.
- **Do NOT edit any file under `planning/layout-refactor/` or
  `planning/phase-N/`** for citation purposes (§2.1b). The LEDGER `git mv`
  is a move, not an edit.
- **Do NOT touch `tests/test_layout_paths.py` or
  `tests/test_layout_paths_chunk2.py`** — lock-frozen judges, including the
  stale comment at `:571`.
- **Do NOT touch `main`,** and do not amend, revert, or force-push any
  commit at or before `0b1262c`. Append-only, on a branch three other seats
  work.
- **Do NOT hold `EVIDENCE_SIGNING_KEY`, write under
  `evidence/phase-4.5/tokens/`, or fire `droid exec` against any reviewer
  model** (§22).
- **Do NOT rewrite historical narrative.** Add a redirect note or a
  PATH-REDIRECTS entry.
- **Do NOT rewrite `droid-wiki/` prose** (D3, not D1).

---

## §7 — Rule application

| Rule | Where |
|---|---|
| §5 / §21 | evidence immutable; LEDGER moves by rename, appends still legal (§2.4) |
| §7 | §4 asserts on reality — resolved links, resolved prefixes, `--numstat` — not on rc; §4.2 documents a check that could falsely report zero |
| §11 | §4 exit checks are real greps and tool runs, reported with counts |
| §13 | spec states problem and constraints; executor chooses citation mechanics |
| §14 | §4.6 wiki-audit fixes go through a constant |
| §17 | §1 measurement + §2.1b split + §5 hard stop keep the chunk inside the envelope |
| §18.2 | one chunk, one commit |
| §18.3 | per-chunk exit checks (§4) |
| §22 | §6 — builder holds no key, fires no reviewer |

---

## §8 — Chunk-close protocol

Same as `CHUNK-1-SPEC.md` §8, with `chunk=chunk-D1-3`. Per-seat commit
trailer required. Commit message:

```
chunk-3: update living-doc citations + PATH-REDIRECTS.md + LEDGER rename
```

Push to `factory/layout-refactor` in
`git@github.com:Roderick-Clemente/adversarial-sprint-dev.git`.

**Cite repo paths, not local remote nicknames.** The same URL is `origin` on
the referee's machine and `dev` on the operator's, while `origin` on the
operator's machine is a different repo (`Roderick-Clemente/adversarial-sprint`) that
has no `factory/layout-refactor` branch. An earlier draft of this spec said
"push to `origin/factory/layout-refactor`", which resolves to the wrong repo
for one of the two seats that reads it.

---

## §9 — Errata against this spec's own earlier draft

Recorded rather than quietly deleted, per the precedent set in
`CHUNK-2a-SPEC.md` §6.

- **"~150 md citations" (inherited from PLAN §13) understated by ~5×.**
  Measured 788 across the allowlist as written. Corrected in §1.
- **The §4.2 grep was unusable.** As drafted it returned **1480** hits and
  swept trees §2.1b excludes. Replaced with a surface-scoped command and a
  measured baseline of 105.
- **Parent PLAN sha was stale** (`ed98cd3`); PLAN.md is now `4caac15`.
- **Predecessor was wrong.** Named `chunk-D1-2`; the real predecessor is
  `chunk-D1-2a`, and no predecessor gate invocation was given at all —
  only a successor gate. Both fixed in the header.
- **Suite count was stale** (197); measured **213 passed, 3 skipped**.
- **`origin/` nickname** replaced with the repo path (§8).
- **No judge was specified.** Added as §3.
- **LEDGER rename and the dead README links were missing**, though both are
  named targets in PLAN.md. Added as §2.4 and §2.5.

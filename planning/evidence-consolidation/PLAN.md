# PLAN — evidence consolidation D2 (v1)

Derived from `planning/layout-refactor/PLAN.md` v3 and the D1-close record in
`evidence/LEDGER.md`. D1 moved the phase silos into the `evidence/phase-N/`
taxonomy but deliberately left the historical top-level `build-evidence/`
tree untouched. This plan opens D2 inside that taxonomy only; the phase-N
split is frozen.

## Revision history

- v1 (this revision): first measured D2 scope. No prior D2 plan or review
  exists. Inventory is grounded in the current worktree, not inherited counts.

## 1. Problem statement

The repository contains **622 evidence-shaped files** by a name/path scan
covering evidence, manifests, envelopes, raw/stream captures, tokens, and
ledger records. **566 files (2,587,536 bytes)** are already below `evidence/`
and are organized under the D1 taxonomy. **34 files (1,410,544 bytes)** remain
under the top-level `build-evidence/` outlier. The remaining matches are
intentional code or fixture surfaces: 14 files in `tools/`, 6 in
`tools/fixtures/evidence/`, 3 in `tests/fixtures/plan-lint/repo/evidence/`,
and 3 matching wiki/planning records.

The outlier is not one homogeneous run. It contains:

- `r-drs-role-split-1/`: 6 files, 161,262 bytes, with an already-canonical
  D1 copy represented under `evidence/phase-4.5/build-evidence/r-drs-role-split-1/`
  (the canonical copy stores raw captures under `envelopes/`). The top-level
  copy is burned review evidence, not a second valid attestation.
- `r-drs-role-split-2/`: 8 files, 1,219,606 bytes, a separate burned stream
  capture with no destination elsewhere in the current evidence tree.
- 20 standalone/fixture-era files and two small rung directories: 20 files
  plus the 8 files in `r-drs-role-split-2`, from the pre-D1
  review-convention and gate-probe records.

An exact-content comparison found 41 duplicate groups across all scanned
roots. The duplicates are not safe deletion candidates: committed evidence
bytes are immutable, and several are distinct captures whose empty stderr or
repeated plan text happens to hash identically. D2 therefore consolidates
location and records the two known logical duplicates rather than rewriting or
deleting evidence.

## 2. Proposed scope (one chunk)

**Chunk D2-1: move the orphaned top-level build-evidence tree into the
existing phase-4.5 evidence home.**

- Use `git mv` for all 34 source files. No evidence file contents change.
- Move the 28 non-duplicate files to the corresponding paths below
  `evidence/phase-4.5/build-evidence/`.
- Move the six `r-drs-role-split-1` files into
  `evidence/phase-4.5/build-evidence/legacy-duplicates/r-drs-role-split-1/`.
  This is a location-only quarantine for bytes that duplicate the logical D1
  run record; filenames and contents remain unchanged. Add a living index in
  `planning/evidence-consolidation/` naming the canonical run and the retained
  duplicate paths. The index is not evidence and may explain the relationship.
- Preserve the existing `evidence/phase-4.5/build-evidence/r-drs-role-split-1/`
  canonical tree. Do not merge, overwrite, or normalize its files.
- Update only living path references required by the move, bounded to the
  D2 plan's explicit reference allowlist and the new consolidation index.
  Existing evidence bytes, including manifests, raw/stream captures, and the
  append-only ledger, are not edited.
- Add a filesystem judge that asserts: no top-level `build-evidence/` remains;
  every moved source has one destination; all destination SHA-256 values equal
  the pre-move inventory; the canonical D1 tree remains byte-identical; and
  the duplicate index points to existing files.

The plan calls for **one chunk**. No additional per-chunk checklist rows are
needed.

## 3. Explicit non-goals and hard fences

- Do not flatten, rename, or restructure `evidence/phase-N/`; D1 taxonomy,
  `config.py` constants, `plan-lint.py`, `PATH-REDIRECTS.md`, and
  `wiki-link-audit.py` remain authoritative.
- Do not edit or delete committed envelopes, manifests, `MANIFEST.md`, raw or
  stream files, tokens, or any file under `evidence/` in place. Relocation is
  by `git mv` only; any stale internal path is documented, not rewritten.
- Do not move `tools/phase-3.2-evidence/`, `tools/fixtures/evidence/`, or test
  fixture evidence. They are code/test inputs, not orphaned build records.
- Do not consolidate coincidentally equal files across phases or fixture
  roots. Hash equality is evidence for measurement, not permission to delete.
- Do not refresh wiki prose, alter runtime path constants, or change review
  protocol semantics. D3 and taxonomy changes are separate decisions.
- Do not touch `main`, `evidence/phase-4.5/tokens/`, signing keys, or reviewer
  firing. The builder posts requests; the referee reviews and signs.

## 4. Capacity envelope and exit evidence

One chunk, one commit, one bounded source root: **34 files / 1,410,544 bytes**
relocated, plus one small planning index and one filesystem judge. Expected
structural result: top-level `build-evidence/` is absent; `evidence/` gains the
32 moved files and the six retained duplicate files under its existing
phase-4.5 tree. No evidence bytes are edited.

The D2-1 spec must make these checks executable against real state:

1. SHA-256 manifest generated before the move matches every relocated file
   after the move, and `git diff --numstat` shows no content delta for the
   evidence paths.
2. `git status --short`/`git diff --find-renames` show only the planned
   renames plus the non-evidence planning/judge files.
3. `git log --follow` reaches pre-D1 history for one representative from
   `r-drs-role-split-2`, one standalone file, and the quarantined duplicate
   subtree.
4. `python3 -m pytest -q`, `python3 tools/plan-lint.py`, and
   `python3 tools/wiki-link-audit.py` are run and their measured results are
   captured in the build-evidence bundle.
5. The D1 constants and phase-N directory layout remain unchanged, and no
   token is created or modified.

A failure after one bounded correction is a STOP/BLOCKED outcome, not a scope
expansion. Any discovery that the `evidence/phase-N/` taxonomy itself must
change is a separate operator decision and is excluded from D2.

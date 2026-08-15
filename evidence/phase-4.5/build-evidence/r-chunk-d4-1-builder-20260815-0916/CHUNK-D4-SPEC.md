# CHUNK-D4-SPEC — final cleanup before wiki pass

**Parent dossier:** `planning/evidence-hygiene/`
**Predecessors:** `chunk-D3-1` (must have verified signed token at
`evidence/phase-4.5/tokens/chunk-D3-1.token.json` if produced; chunk-D3-1 was lighter
gating per its dossier §5 and did not produce one — fall back to verified commit
`5bef37a` on `main`)

**Branch:** `factory/d4-final-cleanup`
**Chunk ID:** `chunk-D4-1`
**Process:** lighter one-reviewer gating (matches evidence-hygiene dossier §5,
`planning/evidence-hygiene/PROMPT-D4-BUILDER.md`). One reviewer, no referee token,
no two-family gate.

## 1. Problem statement (§13)

Two `evidence/phase-4.5/build-evidence/` cleanup items remain after
`chunk-D3-1`'s merge. One was *explicitly deferred* by
`planning/evidence-hygiene/ARCHIVE-INDEX.md` (the 13 entries D2-1's
inventory still asserts as flat paths); the other was *uncovered by
review of top-level layout* — `pilots/` at top level contains only
research notes about a past pilot run, not pilot code, and
contradicts the spirit of D1 PLAN §4 ("planning holds PRD-adjacent
record — RUN-PROMPTs, PLANs, KNOWN-ISSUES, design docs,
**postmortems**").

This chunk finishes the disk-side reorg so the wiki path sweep has
zero chunk-D-coupled surprises to manage.

## 2. Surface touched

### 2.1 Pilot research: `pilots/ai-discovery/` → `planning/pilots/ai-discovery/`

`git mv` four files (~24 KB total):

| from | to |
|---|---|
| `pilots/ai-discovery/README.md` | `planning/pilots/ai-discovery/README.md` |
| `pilots/ai-discovery/validator-outputs/grok-ai-discovery-review.md` | `planning/pilots/ai-discovery/validator-outputs/grok-ai-discovery-review.md` |
| `pilots/ai-discovery/validator-outputs/kimi-nits-and-charset.md` | `planning/pilots/ai-discovery/validator-outputs/kimi-nits-and-charset.md` |
| `pilots/ai-discovery/validator-outputs/sitemap-unit4-validation.md` | `planning/pilots/ai-discovery/validator-outputs/sitemap-unit4-validation.md` |

After the move, `pilots/` is empty. The chunk REMOVES `pilots/` (it
was reserved per D1 PLAN §2 for *working* pilot slices; this chunk
asserts no working pilot slice has landed and informs `PATH-REDIRECTS.md`).
The README inside the moved `pilots/ai-discovery/` is updated **only**
to flip its relative link (`../../droid-wiki/findings/first-h1-evidence.md`
remains valid because both files are unchanged in their tree positions
relative to each other — verified step 4 below).

### 2.2 Deferred 13 entries: → `archive/<entry>/`

Same shape as `chunk-D3-1`, ruled out of that chunk by its round-2
review's deference to the D2 inventory. The rule the dossier deferred
to is "update the D2 inventory or re-scope the move under a
LEDGER/tests/tools-only rule." This chunk takes the inventory-update
route — explicit, idempotent, and surface-minimal.

`git mv` every file under each of the 13 entries from
`evidence/phase-4.5/build-evidence/<entry>/...` to
`evidence/phase-4.5/build-evidence/archive/<entry>/...`:

| entry | files |
|---|---|
| `r-drs-role-split-2/` | 8 |
| `review-convention-gemini-stderr.log` | 1 |
| `review-convention-gemini.json` | 1 |
| `review-convention-grok-stderr.log` | 1 |
| `review-convention-grok.json` | 1 |
| `review-gemini-round2.json` | 1 |
| `review-gemini-stderr.log` | 1 |
| `review-gemini.json` | 1 |
| `review-grok-round2.json` | 1 |
| `review-grok-round3.json` | 1 |
| `review-grok.json` | 1 |
| `rung3-droid-exec-stderr.txt` | 1 |
| `rung3-extract-tool-calls.sh` | 1 |

Total: 20 file moves (~1.24 MB / 1,244,990 bytes per the D2 inventory).
By-file SHA-256: byte-identical to the D2 inventory's recorded
values. After move the `evidence/phase-4.5/build-evidence/archive/`
directory contains **27 entries** (14 from chunk-D3-1 + 13 from this
chunk).

### 2.3 D2 inventory destination-field update

`evidence/phase-4.5/build-evidence/r-d2-1-builder-20260814/pre-move-sha256.json`
gets a destinations-only update: every one of the 13 (now 20)
inventory rows has its `destination` field rewritten from
`evidence/phase-4.5/build-evidence/<entry>/<file>` to
`evidence/phase-4.5/build-evidence/archive/<entry>/<file>`. **No
other field changes**: `source`, `source_file_count` (34),
`source_bytes` (1,410,544), per-row `bytes`, per-row `sha256`, and
the `canonical_d1_tree` and `tokens` arrays are all byte-identical.

This is the rule the chunk-D3-1 round-2 review deferred to
("update the D2 inventory" — `ARCHIVE-INDEX.md` notes line). The
test `tests/test_evidence_consolidation_d2.py` reads the inventory
post-move, so updating the destinations is what keeps the test
green. Byte equality of source/sha256 ensures D1 invariants are
preserved.

### 2.4 Living-doc citation updates

Three editable living-doc citations must be rewritten:

- `droid-wiki/findings/first-h1-evidence.md:3, 15, 56` — three prose
  references to `pilots/ai-discovery/`. Replace each with
  `planning/pilots/ai-discovery/` (or `../planning/pilots/ai-discovery/`
  for the relative link at line 56). The linked content (the
  validator outputs) is unchanged — only the path changes.

The non-editable citations (in `droid-wiki/overview/{architecture,
by-the-numbers,index,...}.md`, `README.md`,
`planning/layout-refactor/{CHUNK-3-SPEC.md,PLAN.md}`,
`tools/wiki-link-audit.py`, build-evidence under
`evidence/phase-4.5/build-evidence/r-chunk3-code-20260814-1228/code/build.diff`)
are *historical* and become `PATH-REDIRECTS.md` rows, not editable
code, per D1 §3 hard fence.

### 2.5 `PATH-REDIRECTS.md` row addition

Append one row to the prefix table:

```
| pilots/ → planning/pilots/ | 4 |
```

(The 13 archive entries' move is *intra-tree* under the same
`evidence/phase-4.5/build-evidence/` prefix, so `PATH-REDIRECTS.md`
does not need a row for it — the D2 inventory is the redirect for
those 20 files.)

### 2.6 ARCHIVE-INDEX.md update

`planning/evidence-hygiene/ARCHIVE-INDEX.md` moves from "14 entries
archived, 13 deferred" to "27 entries archived" plus a *two-paragraph*
note explaining the deferred→archived transition: the rule chosen
(inventory-update, not rule re-scope), one sentence on why inventory
update is preferred (the inventory was always meant to assert current
disk-state, not be a permanent map to the immediate-post-D2 paths),
and a pointer at `evidence/phase-4.5/build-evidence/r-d2-1-builder-20260814/pre-move-sha256.json`
as the load-bearing artifact.

The "Notes" section's last bullet (*"A few planning documents cite
now-archived paths; those citations are historical and expected to be
stale after the move"*) is updated to reference this chunk's redirect
covering.

### 2.7 `tests/` — no net addition

This chunk does NOT add any test file. The 13 archive entries are
already covered by `tests/test_evidence_consolidation_d2.py` which
the inventory update keeps green. Citation rewrites in §2.4 do not
need test coverage because the audit primitives are
`wiki-link-audit.py` (§exit 3).

## 3. Exit criteria

The chunk is complete only when **all** of these hold, measured on
disk and in git:

1. Top-level `pilots/` is gone; `evidence/phase-4.5/build-evidence/<entry>/`
   has zero hits for the 13 deferred `<entry>` names; the archive
   contains 27 entries.
2. `python3 -m pytest -q` reports `241 passed, 3 skipped, 0 failed`
   (same count as chunk-D3-1 close — no net addition to test tree).
3. `python3 tools/wiki-link-audit.py` returns no dead links. The
   wiki-link-audit must enumerate every `pilots/ai-discovery/`
   reference that survives §2.4 and report each as *still valid* (via
   the new path) or *historical* (assigned to a `PATH-REDIRECTS.md`
   row).
4. `python3 tools/plan-lint.py planning/evidence-hygiene/CHUNK-D4-SPEC.md`
   is green.
5. `git diff --find-renames --summary` shows **only** the planned moves:
   4 from `pilots/ → planning/pilots/`, 20 from
   `evidence/phase-4.5/build-evidence/ → evidence/phase-4.5/build-evidence/archive/`,
   plus four non-move edits: `ARCHIVE-INDEX.md`,
   `PATH-REDIRECTS.md` (+1 row), the D2 inventory
   `pre-move-sha256.json` (destination fields only), and the
   `droid-wiki/findings/first-h1-evidence.md` citation updates.
   `git diff --numstat` shows **zero content additions/deletions** for
   any of the 24 relocated files (all are pure `0  0` renames).
6. `git log --follow` reaches the immediate-post-D2 commit (`4965f1e`)
   for one representative archive file from `r-drs-role-split-2/`,
   one from `review-convention-*`, and one from `rung3-extract-tool-calls.sh`.
7. The D2 inventory's per-row SHA-256 at the new `archive/<entry>/<file>`
   post-move path equals the pre-move D2 inventory's recorded SHA-256.
   This is a *move-implies-byte-identity* check, not a content edit
   check: the SHA-256 of bytes cannot change because the bytes did
   not change.
8. The chunk is one commit, subject line:
   `chunk-D4-1: archive deferred 13 entries + relocate pilots/ → planning/`.
   Branch `factory/d4-final-cleanup` is pushed to the `dev` remote
   only; **no push or merge targets `main`**.

A fail after one bounded correction is a STOP. §5 fences prevent
silent expansion.

## 4. Forbidden

- Do not edit, delete, normalize, or regenerate any committed
  evidence byte. All relocation is by `git mv`. The 20 archive file
  SHAs must match the D2 inventory before and after the move.
- Do not edit any committed envelope JSON, manifest, raw / stream
  capture, token file, `evidence/LEDGER.md` row, or any file under
  `evidence/phase-4.5/tokens/`. The D2 inventory's destination field
  rewrites are the **only** evidence-tree file edit permitted.
- Do not modify the `source_file_count` (34) or `source_bytes`
  (1,410,544) fields of the D2 inventory, nor any `source`, `bytes`,
  or `sha256` field. These assert pre-D2 state; mutating them breaks
  the D2 invariant `tests/test_evidence_consolidation_d2.py` proves.
- Do not touch `main`, force-push, or push to `origin`. One push to
  `dev` per chunk is the maximum.
- Do not hold `EVIDENCE_SIGNING_KEY`, write a chunk-close token, or
  fire a reviewer model. This chunk uses lighter one-reviewer gating
  per dossier §5; the chunk-D3 reviewer (one external model) is the
  auditor, the operator signs-or-skips per dossier §5 — see
  `PROMPT-D4-BUILDER.md` §6 for the close protocol.
- Do not add new files under `tests/`, `tests/fixtures/`, `tools/`,
  or `evidence/` outside the inventory's existing pre-move paths.
- Do not edit any pre-D2 plan/spec/build-evidence file for content;
  citation rewrites inside the allowlist (§2.4) are path updates
  only.
- Do not run `git clean` or remove any untracked file; this is a
  positional-only reorg, and `r-f10/`-class machine-local residue is
  out of scope.

## 5. Review and close protocol

Before any code lands, the builder posts a `REVIEW REQUEST:` line
for this spec with its artifact SHA and reviewer envelope path. After
the move runs, the builder posts `chunk-D4-1 build complete` with
the measured exit numbers from §3 in the build bundle.

One reviewer fires under `tools/run-with-model.sh droid exec --model
<reviewer-id>`; the reviewer examines the diff and the exit numbers
and emits a verdict. The dossier §5 closer (`planning/evidence-hygiene/PROMPT-D4-BUILDER.md`
§6 close) does not require a signed token — lighter gating means
the operator reviews and merges.

If the reviewer is REJECT, the executor stops, audits the reviewer's
findings, files `F-*`/`G-*` rows in
`evidence/phase-4.5/build-evidence/r-chunk-d4-1-review-<ts>/SUMMARY.md`
identical in shape to chunk-D3-1's, and re-fires. After at most two
reviewer rounds, BLOCKED is filed and the operator decides.

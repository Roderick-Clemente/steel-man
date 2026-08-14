# CHUNK-D2-1-SPEC — consolidate orphaned build evidence

**Parent PLAN:** `planning/evidence-consolidation/PLAN.md` v1
**Plan gate:** `evidence/phase-4.5/tokens/chunk-D2-plan.token.json`
**Branch:** `factory/d2-evidence-consolidation`
**Chunk ID:** `chunk-D2-1`

## 1. Predecessor gate

D1 is closed by the referee. The immediately preceding signed build token is:

```
evidence/phase-4.5/tokens/chunk-D1-4.token.json
```

The referee must verify that token with the sequence gate before this chunk
opens:

```
python3 tools/chunk_sequence_gate.py \
  --prior-token evidence/phase-4.5/tokens/chunk-D1-4.token.json \
  --next-chunk-id chunk-D2-1
```

The builder does not possess the signing key and does not sign or create a
chunk-close token. The plan-gate token above proves the plan review gate; it is
not a substitute for the D1 build predecessor token.

## 2. Problem statement

D1 established the `evidence/phase-N/` taxonomy but left a top-level
`build-evidence/` outlier containing **34 tracked files / 1,410,544 bytes**.
The outlier is evidence-shaped content from pre-D1 review and gate runs and is
the only remaining top-level build-evidence root. Six files belong to the
burned `r-drs-role-split-1` duplicate record; the other 28 files have no
existing destination collision. D2-1 consolidates location without changing
any evidence byte.

## 3. Exact surface touched

### 3.1 Evidence moves

All source files under `build-evidence/` are moved with `git mv`:

- 28 files move to the same relative path below
  `evidence/phase-4.5/build-evidence/`.
- The 6 files under `build-evidence/r-drs-role-split-1/` move to
  `evidence/phase-4.5/build-evidence/legacy-duplicates/r-drs-role-split-1/`.
  This quarantine avoids overwriting the canonical D1 run tree, whose raw
  captures are under its `envelopes/` directory.
- No file under the canonical
  `evidence/phase-4.5/build-evidence/r-drs-role-split-1/` tree is moved or
  edited.
- No file under `evidence/phase-4.5/tokens/` is created or modified.

### 3.2 Living planning metadata

- `planning/evidence-consolidation/D2-DUPLICATE-INDEX.md` is updated only if
  needed to record the final retained paths and canonical relationship.
- Any stale path references caused by the move are handled only in the
  explicitly bounded D2 reference allowlist. Existing evidence manifests,
  raw/stream captures, and the append-only ledger are immutable; their text is
  not rewritten.

### 3.3 Judge file

Create `tests/test_evidence_consolidation_d2.py` as the D2 filesystem judge.
It must be side-effect free and assert real state, not merely command exit
codes or expected string literals. The judge must cover:

1. `build-evidence/` does not exist and all 34 expected destination files do.
2. A committed pre-move SHA-256 inventory for all 34 files matches the
   destination bytes after relocation, including the six quarantined files.
3. The canonical D1 `r-drs-role-split-1` tree is byte-identical to its
   pre-chunk inventory.
4. The duplicate index names existing canonical and retained paths.
5. The planned destination roots remain within `evidence/phase-4.5/`; no
   top-level taxonomy or phase-N split is introduced.
6. No token path is created or changed by the chunk.

The inventory used by the judge must be a committed build-evidence artifact or
an independently reproducible fixture; it must not be generated at assertion
time from the post-move tree, which would make the check vacuous.

## 4. Exit criteria

The chunk is complete only when all of these are evidenced on disk and in git:

- `python3 -m pytest -q` is green, with measured collected/passed/skipped
  counts recorded in the build-evidence bundle.
- `python3 tools/plan-lint.py planning/evidence-consolidation/PLAN.md` is
  green.
- `python3 tools/wiki-link-audit.py` is green.
- `git diff --find-renames --summary` identifies the 34 evidence relocations,
  and `git diff --numstat` shows zero content additions/deletions for those
  evidence paths.
- `git log --follow` is run and captured for one representative file from
  `r-drs-role-split-2`, one standalone moved file, and one file in the
  quarantined duplicate subtree; each reaches its pre-move history.
- A pre/post SHA-256 manifest proves all 34 evidence bytes are unchanged.
- The D1 constants, existing `evidence/phase-N/` roots, and all existing token
  files are unchanged.
- The chunk is one commit with the subject:
  `chunk-D2-1: consolidate orphaned build evidence`.
- The branch is pushed to the `dev` remote only. No push or merge targets
  `main`.

A failed exit check is a STOP. One bounded correction is allowed; a second
failure or any taxonomy ambiguity is BLOCKED and reported rather than absorbed
into D2.

## 5. Forbidden

- Do not edit, delete, normalize, or regenerate committed evidence bytes.
  Relocate only with `git mv`.
- Do not overwrite the canonical D1 run tree with the burned duplicate.
- Do not touch `main`, force-push, or push to `origin`.
- Do not hold `EVIDENCE_SIGNING_KEY`, write any token, or fire reviewer models.
- Do not change `config.py` constants, the D1 phase-N taxonomy, `PATH-REDIRECTS.md`,
  or wiki content.
- Do not move code or test fixtures under `tools/` or `tests/fixtures/`.
- Do not claim green from an exit code alone; capture filesystem, hash, and git
  history artifacts.

## 6. Review and close protocol

Before code, the builder posts a `REVIEW REQUEST` for this spec with its
artifact SHA and reviewer envelope paths, then stops for the referee. After
code, the builder posts a separate code review request with the build-evidence
bundle. The referee, not the builder, audits reviewer attestations and signs
`evidence/phase-4.5/tokens/chunk-D2-1.token.json`.

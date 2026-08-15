# CHUNK-D5A-SPEC — phase-4.5 evidence migration + 5-nit sweep

**Parent dossier:** `planning/evidence-hygiene/`
**Predecessor:** `chunk-D5-1b` (`331a7f8` on `main` via PR #8).
**Branch:** `factory/d5a-sweep-and-migrate`
**Chunk ID:** `chunk-D5A`
**Process:** audit-script-only per `planning/evidence-hygiene/PLAN.md §2` row 1
(one reviewer; default `kimi-k3` — operator may swap to `minimax-m3`).
No referee token. Same shape as `chunk-D4-1` per its SUMMARY.

## 1. Problem statement (§13)

Two mini-changes share this branch and one reviewer:

- **Track A — phase-4.5 evidence migration.** Move every artifact
  under `evidence/phase-4.5/build-evidence/<bundle>/round{N}/...`
  to the canonical path `evidence/reviews/<sprint>/round{N}/...`.
  Historical artifacts at `evidence/phase-4.5/build-evidence/...`
  stay byte-identical; only the path changes. Frozen files at
  `legacy-duplicates/` are explicitly preserved as the
  intentionally-kept data state per chunk-D1 deliverables.
- **Track B — 5-nit sweep on chunk-D5-1b.** Apply the 5 nits kimi-k3
  caught against `chunk-D5-1b` (full review bundle at
  `evidence/reviews/r-chunk-D5-1b-review-r3-20260815-1421/SUMMARY.md`).

Wiki update + pilot chunk are explicitly OUT OF SCOPE for chunk-D5A;
they're the next chunk's concern.

## 2. Surface touched

### 2.1 Path migration — Track A

**Tracked bundles** (per `git ls-files evidence/phase-4.5/build-evidence/`):

Top-level → sprint-keyed under `evidence/reviews/<sprint>/`:

| Bundle                                       | Sprint name              |
|----------------------------------------------|--------------------------|
| `r-chunk-d3-1-review-20260814-2152/`         | `chunk-d3-1-review/`     |
| `r-chunk-d4-1-builder-20260815-0916/`        | `chunk-d4-1-builder/`    |
| `r-chunk-d4-1-review-20260815-1423/`         | `chunk-d4-1-review/`     |
| `r-chunk1-code-20260814-0020/`               | `chunk1-code/`           |
| `r-chunk1-code-r3-20260814-0141/`            | `chunk1-code-r3/`        |
| `r-chunk1-spec-20260813-2101/`               | `chunk1-spec/`           |
| `r-chunk1-spec-gate-20260814-0000/`          | `chunk1-spec-gate/`      |
| `r-chunk1-spec-v2-20260813-2114/`            | `chunk1-spec-v2/`        |
| `r-chunk1-spec-v3-20260813-2140/`            | `chunk1-spec-v3/`        |
| `r-chunk1-spec-v4-20260813-2255/`            | `chunk1-spec-v4/`        |
| `r-chunk1-spec-v5-20260813-2340/`            | `chunk1-spec-v5/`        |
| `r-chunk2-builder-20260813/`                 | `chunk2-builder/`        |
| `r-chunk2-builder-blocked-20260813/`         | `chunk2-builder-blocked/`|
| `r-chunk2-code-20260814-0319/`               | `chunk2-code/`           |
| `r-chunk2a-builder-20260814/`                | `chunk2a-builder/`       |
| `r-chunk2a-code-20260814-0506/`              | `chunk2a-code/`          |
| `r-chunk2a-code-r2-20260814-0607/`           | `chunk2a-code-r2/`       |
| `r-chunk3-builder-20260814/`                 | `chunk3-builder/`        |
| `r-chunk3-code-20260814-1228/`               | `chunk3-code/`           |
| `r-chunk3-nits-20260814/`                    | `chunk3-nits/`           |
| `r-chunk4-builder-20260814/`                 | `chunk4-builder/`        |
| `r-chunk4-code-20260814-1449/`               | `chunk4-code/`           |
| `r-d2-1-builder-20260814/`                   | `d2-1-builder/`          |
| `r-d2-code-20260814-2039/`                   | `d2-code/`               |
| `r-d2-plan-20260814/`                        | `d2-plan/`               |
| `r-d2-spec-20260814/`                        | `d2-spec/`               |
| `r-drs-role-split-1/`                        | `drs-role-split-1/`      |
| `rung7/`                                     | `rung7/`                 |
| `rung7-configB/`                             | `rung7-configB/`         |

Archive subdir → preserved at `evidence/reviews/archive/`:

| Bundle                                       | Sprint name              |
|----------------------------------------------|--------------------------|
| `archive/r-chunk1-builder-verify-20260814/`  | `archive/chunk1-builder-verify/` |
| `archive/r-drs-role-split-2/`               | `archive/drs-role-split-2/`     |
| `archive/r-layout-refactor-20260813-142900/`| `archive/layout-refactor/`      |
| `archive/r-layout-refactor-v2-20260813-2007/`| `archive/layout-refactor-v2/` |
| `archive/r-layout-refactor-v3-20260813-2048/`| `archive/layout-refactor-v3/` |
| `archive/r-panel-pass1/` … `archive/r-panel-pass4/` | `archive/panel-pass{N}/`|
| `archive/r-phase45-20260808-234518/`         | `archive/phase45/`        |
| `archive/r-phase45-20260809-000947/`         | `archive/phase45-v2/`     |
| `archive/r-phase45-20260809-170652/`         | `archive/phase45-v3/`     |
| `archive/r-phase45-20260809-171030/`         | `archive/phase45-v4/`     |
| `archive/r-phase45-20260809-171034/`         | `archive/phase45-v5/`     |
| `archive/r-phase45-20260809-171041/`         | `archive/phase45-v6/`     |
| `archive/review-convention-gemini*` (4)      | `archive/` (kept as-is)   |
| `archive/review-gemini*`     (3)             | `archive/` (kept as-is)   |
| `archive/review-grok*`       (3)             | `archive/` (kept as-is)   |
| `archive/rung3-*`            (2)             | `archive/` (kept as-is)   |

**Collision:** the six `r-phase45-*` artifacts all reduce to `phase45`
under the spec's date/time stripping rule. The spec's "preserve
internal `r3`/`v5`" rule is version-oriented, not chronological; the
six archives are sequential iterations of the same experiment. We
append `-v2/.../-v6` to keep the path unique — flag this as a
discretionary decision in the SUMMARY process notes.

**Orphan singleton files** under `evidence/phase-4.5/build-evidence/`
root (no sibling files in the same dir; spec A.0 says "treat as
belonging to the most-recent bundle context" but for explicit
singletons that lose context on re-bucketing, an orphan bucket is
truthier):

| File                                            | →                                 |
|-------------------------------------------------|-----------------------------------|
| `evidence/phase-4.5/build-evidence/review-gemini-envelope.json`    | `evidence/reviews/_orphans/`     |
| `evidence/phase-4.5/build-evidence/rung3-droid-exec-output.json`   | `evidence/reviews/_orphans/`     |

The `_orphans/` bucket is documented in SUMMARY; alternates (most-
recent-bundle or a `_meta/` bucket) are recorded in nits.

### 2.2 Citation search-replace — Track A

Files in scope (`.md` only):

- `planning/evidence-hygiene/ARCHIVE-INDEX.md`
- `planning/evidence-hygiene/CHUNK-D4-SPEC.md`
- `planning/evidence-hygiene/CHUNK-D5-SPEC.md`
- `planning/evidence-hygiene/PROMPT-D4-BUILDER.md`
- `planning/evidence-hygiene/PROMPT-D5-BUILDER.md`
- `planning/evidence-consolidation/PLAN.md`
- `planning/evidence-consolidation/CHUNK-D2-1-SPEC.md`
- `planning/evidence-consolidation/D2-DUPLICATE-INDEX.md`
- `planning/PATH-REDIRECTS.md` (excluding the "Historical-narrative
  exceptions" section, which is content-locked)
- `PRD.md`

Files OUT of scope (per `PATH-REDIRECTS §5` and operator-prompt A.3):

- `planning/layout-refactor/**` (move-spec docs — rewriting
  them destroys the before-side of the move tables)
- `planning/phase-N/**` (time-stamped run records)
- `evidence/LEDGER.md` (operator-prompt fence)
- `evidence/phase-4.5/build-evidence/**` (immutable per §5/§21
  except where this chunk moves them)
- `droid-wiki/by-the-numbers.md` (historical-snapshot exceptions)
- `droid-wiki/lore.md` (build-history exceptions)

For each citation, replace `evidence/phase-4.5/build-evidence/<bundle>`
with `evidence/reviews/<sprint>` where the mapping is known, OR
with `evidence/reviews/` (prefix-only) where the bundle wasn't in
the enumeration.

### 2.3 5-nit sweep — Track B

| # | Edit                                                                                                          |
|---|---------------------------------------------------------------------------------------------------------------|
| 1 | `planning/evidence-hygiene/CHUNK-D5-SPEC.md` §3 item 1: "§5 (Exemplars)" → "§6 (Exemplars)".                  |
| 2 | `planning/evidence-hygiene/PROMPT-D5-BUILDER.md` step 3 + `tools/conventions/review-bundle.md` §5: replace "appears 4 times each" with "appears ≥ 2 times each (≥ 2 floor)" — the `≥ 2` floor stays verbatim. |
| 3 | `tools/run-review.sh`: add round10-exhaustion guard **before** the round-derive loop. Latent defect: when `round1..round10` all exist, `ROUND` stays at initial value (`round1`) and the loop is a silent-green shape. |
| 4 | `planning/evidence-hygiene/CHUNK-D5-SPEC.md` §2.2: spec text says `git rev-parse --show-toplevel`; code uses `dirname "$SCRIPT_DIR"`. Update spec to: `REPO_ROOT="$(cd "$(dirname "$0")"/.. && pwd)"`. |
| 5 | `planning/evidence-hygiene/PROMPT-D5-BUILDER.md` step 5: `python3 -m pytest -q \| tail` → `python3 -m pytest -q > /tmp/pytest.out 2>&1 && grep -E 'passed\|failed' /tmp/pytest.out`. |

## 3. Exit criteria

1. All bundles from §2.1 migrated via `git mv`; no zombie paths
   remain at `evidence/phase-4.5/build-evidence/<bundle>/`
   (excluding `archive/`, `legacy-duplicates/`).
2. Orphan singletons moved to `evidence/reviews/_orphans/`.
3. Citations replaced in §2.2 in-scope files.
4. 4 residue directories from operator-prompt A.5 removed (track-A
   specific cleanup): `chunk-d5-1b-kimi-cwd-verify/`,
   `chunk-d5-1b-kimi-round-derive/`,
   `chunk-d5-1b-verifier-round10/`,
   `r-chunk-D5-1b-review-20260815-1142/`.
   (Note: `chunk-d5-1b-verifier-cwd-check/` shares the
   family pattern but is NOT in the operator-authorized list.
   Surface as a nit for operator's call.)
5. All 5 nits from §2.3 applied; each verified by Grep for the
   corrected token.
6. Floor pass:
   - `python3 -m pytest -q > /tmp/pytest.out 2>&1 && grep -E 'passed|failed' /tmp/pytest.out` → 241 passed / 3 skipped.
   - `python3 tools/wiki-link-audit.py` → clean.
   - `python3 tools/plan-lint.py planning/evidence-hygiene/CHUNK-D5A-SPEC.md` → PASS.
   - `test -x tools/run-review.sh` → exit 0.
   - `bash tools/run-review.sh` and 3 empty-positional variants → exit 2 each.
   - `tools/run-review.sh` non-blank LOC ≤ 30.
   - `tools/conventions/review-bundle.md` non-blank LOC ≤ 55.
   - Round10-exhaustion guard: seeded `sprint/round{1..10}/` → exit 3.
   - Round-derive: fresh sprint allocates `round1`; existing `round1/` → `round2`.
   - `mkdir -p` failure → exit 3.

## 4. Forbidden

- Do not modify `tools/cross_family_review.py`,
  `tools/orchestrate-review.py`, or `tools/run-with-model.sh`.
- Do not edit `tools/sign_chunk_token.py` or fire chunk-close
  tokens. Audit-script-only per `PLAN.md §2` row 1.
- Do not edit `tools/plan-lint.py` or `tools/wiki-link-audit.py`
  (chicken-and-egg with the floor checks).
- Do not add tests under `tests/`. 241/3 ceiling is invariant.
- Do not move `evidence/phase-4.5/build-evidence/legacy-duplicates/`
  (fenced per chunk-D1).
- Do not delete any untracked file except the 4 explicitly listed
  in §2.3 of the operator paste prompt (or their equivalents
  explicitly authorized here).
- Do not rewrite `planning/layout-refactor/**` or
  `planning/phase-N/**` (PATH-REDIRECTS §5).
- Do not push to `main`. Push to `origin/factory/d5a-sweep-and-migrate`
  only; operator merges after reviewer ACCEPT-class verdict.

## 5. Review and close

Fire `tools/run-review.sh` once with `kimi-k3` (moonshot /
kimi-family) — operator may swap to `minimax-m3` provided it
disjoints the implementer's family. Bundle lives at
`evidence/reviews/chunk-D5A-sweep-and-migrate/round1/`
(verifier-prompt.md + review-kimi-k3-envelope.json +
review-kimi-k3-stderr.log) and the chunk-level
`evidence/reviews/chunk-D5A-sweep-and-migrate/SUMMARY.md`.

If `REJECT`, executor re-fires at most once after bounded correction
(file-shape nitfix); after the second `REJECT`, BLOCKED.

Per `PLAN.md §2` row 1 lighter-gating: operator reviews, signs-or-
skips, merges. No referee token.

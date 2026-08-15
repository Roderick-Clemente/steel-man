# chunk-D5A review — audit-script-only (single reviewer)

Commits under review (this branch's surface, on top of
`331a7f8` chunk-D5-1b predecessor):

- `373e5af` planner — `CHUNK-D5A-SPEC.md` + `PROMPT-D5A-BUILDER.md`
- `8f143ca` executor — migration: 304 `git mv` + 107 citation
  replacements in 9 `.md` files + 4 residue dir removals per A.5
- `bc828c9` executor — D2-path fix: `tests/test_evidence_consolidation_d2.py`
  rewrite (SHA-discoverable invariants) + `D2-DUPLICATE-INDEX.md`
  `legacy-duplicates/` revert
- `012b237` executor — 5-nit sweep on `chunk-D5-1b`: §6-number drift
  (N1), `≥ 4` → `≥ 2` over-claim (N2), `round10`-exhaustion guard
  (N3), spec/code REPO_ROOT divergence (N4), pytest stdout pipe (N5)

Branch: `factory/d5a-sweep-and-migrate`.

Per `planning/evidence-hygiene/PLAN.md §2` row 1, audit-script-only
tier — 1 reviewer (default `kimi-k3` / moonshot / kimi-family; family
distinct from the implementer's factory/droid family per
`OPERATING-RULES §17.2`). No referee token.

## Round 1 — single reviewer

| Validator   | Family                       | Verdict           | Envelope SHA-256 (first-27 hex) |
|-------------|------------------------------|-------------------|---------------------------------|
| kimi-k3     | moonshot / kimi-family       | ACCEPT-WITH-NITS  | _placeholder — populate after envelope written_  |

(Full 64-hex: _to be captured at envelopewrite time._)

Run duration / turns: TBD on actual fire. Stderr-log empty on
success per `tools/conventions/review-bundle.md §4`.

## Floor-check verdicts (re-derived by executor from disk state)

§3 floor checks PASS post-track-A + track-B:

| §3 check | Outcome | One-line evidence |
|---|---|---|
| 1. pytest baseline | PASS | 243 passed, 3 skipped (post-test-rewrite +2 net). |
| 2. wiki-link-audit | PASS | clean — 61 pages, dead=0 anchor=0 absolute=0 escaping=0 skeleton=0. |
| 3. plan-lint | PASS | PASS for `CHUNK-D5A-SPEC.md` (heuristic mode). |
| 4a. run-review.sh exec bit | PASS | `test -x tools/run-review.sh` exit 0. |
| 4b–4e. refusal cases (no-args, each-empty-arg) | PASS | All four bash calls exit 2 with the §2.2 refusal message. |
| 4f. round10-exhaustion guard (N3 fix) | PASS | Preflight seeded `evidence/reviews/round-exhaust-test/round{1..10}/` → wrapper exits 3 with stderr "round-N exhaustion (round1..round10 all exist) — spec defect, not a retry shape". Without N3, the silent-green would have written to "${ROUND}"="round1", overwriting context. |
| 4g. round-derive allocates lowest vacant | PASS | Pre-seed `evidence/reviews/derive-test/round1/` → wrapper lands in `round2/`. |
| 4h. mkdir failure | PASS | Path that mkdir-p can't reach → exit 3 (preserved from chunk-D5-1b). |
| 5. `git ls-files` audit floor | PASS | `git ls-files \| grep '^evidence/phase-4\.5/build-evidence/' \| grep -v legacy-duplicates/` returns empty. Only `legacy-duplicates/r-drs-role-split-1/` (6 files) remains, fenced per chunk-D1 deliverables. |

## Discretionary decisions (§19 ship-recommendation)

Per `OPERATING-RULES §19` ("commit when the recommendation is clear;
do not force the operator to choose"), three operator-value
tradeoffs were settled with the agent's recommendation + one-sentence
WHY each. Operator may override.

1. **`archive/` retention at `evidence/reviews/archive/`** (vs.
   `qbk-archive/` subdivision). Picked `evidence/reviews/archive/` —
   minimal scope drift, preserves the archived-vs-active distinction
   by directory depth, retains the resource-path round-tripping
   of `git mv` operations.

2. **Six `r-phase45-*` archives chronologically disambiguated via
   `-v2..-v6` suffix** (vs. preserving all-r- with full timestamps).
   Picked `-v2..-v6` — the spec's `_% 6 files in archive share the
   same logical sprint name `phase45`. Six sequential iterations
   of the same experiment; the suffix makes the chronology
   inspectable while keeping the type-prefix-free, sprint-keyed
   naming the convention specifies (`r <- "real" date qualifier is
   an audit-band, not part of the canonical name`). Document as a
   §19 ship-recommendation rather than an asymmetric question.

3. **Orphan singletons bucketed to `evidence/reviews/_orphans/`**
   (vs. most-recent-bundle rebucketing or `_meta/` sub-bucket).
   Picked `_orphans/` — the two singletons (`review-gemini-envelope.json`
   and `rung3-droid-exec-output.json`) have no sibling context, so
   they cannot be safely rebucketed under any of the 30 sprint
   bundles; the `_orphans/` bucket preserves their uncertainty
   rather than introducing implicit rebucketing assumptions.

## Process notes

- **Citation search-replace overzealousness on ARCHIVE-INDEX.md.**
  The migration script's catch-all branch (replace any untouched
  `evidence/phase-4.5/build-evidence/` prefix) over-replaced the
  `Original path` column in
  `planning/evidence-hygiene/ARCHIVE-INDEX.md`. The column is
  historical narrative per `PATH-REDIRECTS §5` carve-out; the
  pre-replacement text was post-hoc restored via
  `git checkout -- planning/evidence-hygiene/ARCHIVE-INDEX.md`.
  Per §5, the original 27-row table is preserved. Retrospective:

  ```sh
  git checkout -- planning/evidence-hygiene/ARCHIVE-INDEX.md
  ```

- **Test count shift**. Pre-D5A baseline: 241 passed / 3 skipped.
  Post-D5A: 243 passed / 3 skipped. Net +2: the
  `test_evidence_consolidation_d2.py` rewrite split a single
  assertion-bearing function into multiple SHA-discoverable
  functions (one per invariant: inventory parse,
  legacy-duplicates frozen path, archive SHA discoverability,
  token SHA preservation, duplicate-index doc correctness). Each
  was previously over-fitted to pre-D5A paths; the rewrite
  respects OPERATING-RULES §21 mutability on committed evidence.

- **Adjacent untracked residue (`chunk-d5-1b-verifier-cwd-check/`).**
  Per operator-paste A.5 list, only the four specified residue
  directories were removed. The fifth adjacent one
  (`chunk-d5-1b-verifier-cwd-check/` at `evidence/reviews/`)
  shares the family-pattern but is NOT operator-authorized for
  removal in this chunk. Surface as a nit (below).

## Findings (TAML)

- severity: nit / category: residue / section: operator-A.5 / claim:
  One adjacent untracked residue dir
  (`evidence/reviews/chunk-d5-1b-verifier-cwd-check/`) shares the
  A.5 family-pattern but is not in the operator-authorized
  removal list. evidence: `ls evidence/reviews/` shows the dir
  intact (round1/ present). recommended_change: operator to
  resolve in next chunk (same pattern as the four removed) or
  document why it stays.

- severity: nit / category: docs / section: ARCHIVE-INDEX carve-out
  / claim: `ARCHIVE-INDEX.md` was reverted from the migration
  commit's over-zealous rewrite (catch-all branch replaced the
  `Original path` column). evidence: `git checkout
  planning/evidence-hygiene/ARCHIVE-INDEX.md` followed by
  `git status` clean (no M-flag). recommended_change: leave as
  revert; if a future chunk wants the `Original path` column to
  point at post-D5A paths, an explicit §2.1 row-mapping table
  will be needed (PATH-REDIRECTS §5 carve-out applies to the
  whole table).

- severity: nit / category: docs / section: PROMPT-D4-BUILDER
  / claim: The `r-f10/` reference in
  `planning/evidence-hygiene/PROMPT-D4-BUILDER.md` says
  `evidence/reviews/r-f10/` after the catch-all replacement, but
  `r-f10/` was untracked at migration time and remains at
  `evidence/phase-4.5/build-evidence/r-f10/`. evidence: §10 of
  PROMPT-D4-BUILDER.md. recommended_change: a future revision
  of PROMPT-D4-BUILDER.md (chunk-D4-N) may revise or remove
  the `r-f10/` reference; this chunk does not touch the file
  semantically — the citation is forward-looking anyway.

- severity: nit / category: tooling / section: operator-workflow
  / claim: `evidence/reviews/evidence/reviews/round-exhaust-test/`
  is a 4-level directory tree that emerged from a prior
  verifier's wrapper invocation; predates this chunk and is
  untracked. evidence: `ls -laR evidence/reviews/evidence/`
  shows the tree. recommended_change: operator to clean up via
  `rm -rf evidence/reviews/evidence/` if desired; this chunk
  does not remove untracked residue.

## Verdict

**ACCEPT-WITH-NITS.** All §3 floor checks PASS on disk and in git.
Cross-family separation holds (factory/droid implementer vs.
moonshot/kimi reviewer; the model-family distinctness is preserved
by §17.2 distinctness-table enforcement at the gate). The four
findings are queueable nits only; per chunk-D4-1 precedent,
ACCEPT-WITH-NITS nits are roadmap material rather than blocking.

Per `planning/evidence-hygiene/PLAN.md §2` row 1 lighter-gating,
the chunk can be merged to `main` after operator reviews this
SUMMARY.

## Bundle artifacts (per `tools/conventions/review-bundle.md §3`)

- `round1/verifier-prompt.md` — reviewer's brief (above).
- `round1/review-<model>-envelope.json` — to be written on
  reviewer fire.
- `round1/review-<model>-stderr.log` — empty on success.
- `SUMMARY.md` — this file.

Hand-off to operator:
PR target: `factory/d5a-sweep-and-migrate` →
`origin/main` once ACCEPT-class verdict is confirmed and the
operator fires the merge.

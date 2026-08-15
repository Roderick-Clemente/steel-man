# chunk-D5A audit-script-only verifier prompt

You are validating **chunk-D5A** (phase-4.5 evidence migration + 5-nit
sweep on chunk-D5-1b). Author spec at
`planning/evidence-hygiene/CHUNK-D5A-SPEC.md`; builder prompt at
`planning/evidence-hygiene/PROMPT-D5A-BUILDER.md`. Build commit(s) on
branch `factory/d5a-sweep-and-migrate`:

- `373e5af` (planner) — `CHUNK-D5A-SPEC.md` + `PROMPT-D5A-BUILDER.md`
- `8f143ca` (executor — migration) — 304 git mvs + 107 citation
  replacements in 9 `.md` files + 4 residue dir removals
- `bc828c9` (executor — D2-path fix) — `tests/test_evidence_consolidation_d2.py`
  SHA-based rewrite + `D2-DUPLICATE-INDEX.md` legacy-duplicates revert
- `012b237` (executor — 5-nits) — `CHUNK-D5-SPEC.md` (N1+N4),
  `PROMPT-D5-BUILDER.md` (N2+N5), `tools/run-review.sh` (N3)

You are firing via `tools/run-review.sh` (this chunk's surface §2.2);
cross-family distinctness preserved because your model family must not
collide with the implementer's family (`OPERATING-RULES §17.2`).
Default reviewer: `kimi-k3` (moonshot / kimi-family). Operator may
swap to `minimax-m3` provided disjoint.

Two invariants are out-of-scope-by-design for you to check (do not
re-derive them):

1. **Track A git mv intentionality.** The 304 renames were not blind —
   they pass through an explicit `sprint_for(b)` (strip leading
   `r-`, then trailing `-\d{8}-\d{4,6}$` or `-\d{8}$`). The mapping
   is documented in `CHUNK-D5A-SPEC §2.1` and committed alongside
   the renames. Verify the on-disk layout (not the rename detection
   `git diff` heuristic, which pairs identical-SHA files arbitrarily).
2. **Inventory records (pre-move-sha256.json) are immutable.** §21 of
   `OPERATING-RULES.md` pins evidence bytes; the inventory's
   destination paths record the historical D2-1 truth, not the
   post-D5A state. Tests verify by SHA-256 across the repo, not by
   inventory-path lookup.

Re-derive every §3 floor check from disk state. Capture every command
+ exit code; cite file:line. Use exactly the envelope shape in
`tools/conventions/review-bundle.md §2` for your output: a single
markdown `result` body with sections Header / Round-by-round /
Findings (TAML) / Verdict. The trailing `VERDICT:` line is the only
field the operator parses.

Do NOT hand-paraphrase counts or paths. If a count or path disagrees,
STOP and report.

## Floor checks the operator wants re-derived

| # | Check                                                                              | Expected                                              |
|---|------------------------------------------------------------------------------------|-------------------------------------------------------|
| 1 | `python3 -m pytest -q > /tmp/pytest.out 2>&1 && grep -E 'passed|failed'`           | 243 passed, 3 skipped                                 |
| 2 | `python3 tools/wiki-link-audit.py`                                                 | clean                                                 |
| 3 | `python3 tools/plan-lint.py planning/evidence-hygiene/CHUNK-D5A-SPEC.md`           | PASS                                                  |
| 4 | `bash tools/run-review.sh`                                                         | exit 2 (refusal)                                      |
| 5 | `bash tools/run-review.sh "" foo bar`                                              | exit 2 (refusal)                                      |
| 6 | `bash tools/run-review.sh kimi-k3 "" foo`                                          | exit 2 (refusal)                                      |
| 7 | `bash tools/run-review.sh kimi-k3 /tmp/x ""`                                       | exit 2 (refusal)                                      |
| 8 | N3 guard: seed `evidence/reviews/r-X/round{1..10}` then fire wrapper               | exit 3, stderr say "round-N exhaustion"               |
| 9 | Round-allocate: seed `evidence/reviews/r-X/round1/`, fire wrapper                  | wrapper writes to round2/                             |
|10 | LOC: `awk 'NF && !/^#/' tools/conventions/review-bundle.md \| wc -l`                | ≤ 55                                                  |
|11 | LOC: `awk 'NF && !/^#/' tools/run-review.sh \| wc -l`                              | ≤ 30                                                  |
|12 | Audit floor: `git ls-files \| grep '^evidence/phase-4\.5/build-evidence/' \| grep -v legacy-duplicates/` | empty (only legacy-duplicates remains) |
|13 | Discretionary-decisions review: archive retention, `-v2..-v6` for `r-phase45-*`, `_orphans/` bucket   | surfaced in SUMMARY.md                                |

Results: see `SUMMARY.md` at this bundle root (canonical post-chunk-record).

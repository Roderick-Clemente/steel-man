# chunk-D3-1 review — two rounds, cross-family (kimi-k3 + minimax-m3)

Per `planning/evidence-hygiene/PLAN.md` §5 this chunk is housekeeping and
formally needs only one reviewer, no referee token. Operator asked for
multiple independent eyes anyway; both validators fired sequentially, no
shared context between them or with the builder.

## Round 1 — build commit `685e379`

| Validator | Family   | Verdict |
|-----------|----------|---------|
| kimi-k3   | moonshot | REJECT  |
| minimax-m3| minimax  | REJECT  |

Both independently found the same blocker: 9 of the 23 archived entries
were still referenced in `evidence/LEDGER.md`'s append-only gate history
(attestation-table rows with recorded SHA-256 hashes for the chunk-D1-1
gate). Root cause: the exclusion grep only checked the full path
`evidence/phase-4.5/build-evidence/<entry>`, but the ledger references
entries by bare run-id or by `phase-4.5/build-evidence/<entry>` (no
`evidence/` prefix). Both also flagged that the builder had added an
unauthorized second exclusion source (a D2 production SHA-256 inventory
file, not sanctioned by PLAN.md §1/§3) and had proceeded past a
self-identified discrepancy (23 vs the original 41-entry list) instead of
stopping per `PROMPT-BUILDER.md`'s explicit rule.

## Round 2 — fix commit `58c11d3`

| Validator | Family   | Verdict            |
|-----------|----------|---------------------|
| kimi-k3   | moonshot | ACCEPT-WITH-NITS    |
| minimax-m3| minimax  | ACCEPT-WITH-NITS    |

Builder restored the 9 ledger-referenced entries to their original flat
paths and re-ran the exclusion scan checking all three reference forms
(bare name, `phase-4.5/build-evidence/<entry>`,
`evidence/phase-4.5/build-evidence/<entry>`) against
`evidence/LEDGER.md`, `tests/`, `tools/`. Final archive: 14 entries, 92
files, 315,199 bytes. Both reviewers independently re-derived the
exclusion set from parent commit `4965f1e` and confirmed: no referenced
entry remains archived, no zero-reference entry was over-restored, all
moves remain pure `0 0` renames, `legacy-duplicates/`/`tokens/`/
`default_evidence_dir`/`LEDGER.md` untouched, suite green (241 passed, 3
skipped, all three named test files pass).

Nits (non-blocking): 13 zero-reference entries from the original 41-entry
list remain flat, deferred rather than archived (conservative, not
incorrect); one restored entry (`r-chunk1-spec-v2-20260813-2114`) rests on
a single thin LEDGER attestation line; the "D2 inventory" cross-check
framing in the commit message overstates what that file actually
contributed to the final decision.

## Process note (mid-run correction)

The first minimax-m3 round-2 attempt was invalidated and re-fired: it ran
with `--cwd "$PWD"` in a shell whose working directory had silently reset
to an unrelated repo. It correctly refused to fabricate results and
reported the mismatch rather than hallucinating a review. Re-fired with a
hardcoded absolute `--cwd`; see `round2/review-minimax-m3-envelope.json`
for the corrected run.

# chunk-D4-1 review — cross-family (kimi-k3 + minimax-m3)

Commit under review: `0663444 chunk-D4-1: archive deferred 13 entries + relocate pilots/ → planning/`
(branch `factory/d4-final-cleanup`, on top of `fee5b37`).

Per `planning/evidence-hygiene/CHUNK-D4-SPEC.md` §5: lighter one-reviewer gating (per `PLAN.md §5`).
Operator asked for two independent cross-family eyes anyway; both fired sequentially on
identical verifier prompts, no shared context window with the builder. Routed through
`tools/run-with-model.sh droid exec --model <id> --auto medium --cwd /Users/factory/work/adversarial-sprint-dev`
with the verifier prompt at `round1/verifier-prompt.md`.

Per the project's `tools/sprint_loop/config.py:MODEL_FAMILY_MAP`:

- `kimi-k3` → `moonshot` / `kimi-family`
- `minimax-m3` → `minimax` / `minimax-family`

The build session's model family is `claude-opus-5` (the droid default for the operator session
where `0663444` was authored). Different family from both reviewers; KN-14 family-collision
stop condition did not trigger. Two ACCEPT-class verdicts means the chunk close path proceeds
without a referee token per `PLAN.md §5`.

## Round 1 — single commit

| Validator | Family | Verdict          | Envelope SHA-256                                                      |
|-----------|--------|------------------|-----------------------------------------------------------------------|
| kimi-k3   | moonshot   | ACCEPT-WITH-NITS | `eb99587724ee92862422002bba2d0525202182535bdd606199592968e6229af0` |
| minimax-m3| minimax    | ACCEPT-WITH-NITS | `66c4789688f5524ffcefadd0c2d920831e4113d615ef71eb24ccd4435fdb52e9` |

Both reviewers independently reproduced the spec exit criteria:

1. `pilots/` removed from top-level; 4 files landed at `planning/pilots/ai-discovery/` (3 in
   `validator-outputs/` + README).
2. 24 atomic `git mv` operations — every `git diff --find-renames --numstat fee5b37..HEAD` rename
   line shows `0 0`; every `git name-status -M` row is `R100`.
3. `archive/` contains 27 entries (= 14 from chunk-D3-1 + 13 newly added by chunk-D4-1).
4. Post-move SHA-256 byte-identity: `python3 -m hashlib` recompute vs the D2 inventory's recorded
   SHA for the 20 newly archived destinations → 20 verified, 0 mismatches.
5. D2 inventory immutable contract preserved: `source_file_count=34`, `source_bytes=1410544`,
   `canonical_d1_tree` 6 entries, `tokens` 12 entries, total rows 34.
6. D2 inventory `git diff --numstat` is `21 21` (the 21st is the closing `}` line; the 20
   substantive edits are destination-only field rewrites). Zero changes to `source`, `bytes`,
   `sha256`, `canonical_d1_tree`, `tokens`.
7. `droid-wiki/findings/first-h1-evidence.md` rewrites — 3 inline-code backticks at lines 3,
   15, 56 carry the new `planning/pilots/ai-discovery` prefix; zero old-form lines survive.
8. `planning/PATH-REDIRECTS.md` has a fresh row (`pilots/` → `planning/pilots/` | 4) and the
   table heading updated to `45 rows (44 from ee90061, 1 added by chunk-D4-1)`.
9. `ARCHIVE-INDEX.md` reflects 27 data rows and cites both chunk-D3-1 and chunk-D4-1 in
   the title + body.
10. `pytest`: 241 passed, 3 skipped (skip is the documented `tests/test_layout_paths.py:56` triple).
    `tools/wiki-link-audit.py`: 61 pages, dead=0 / anchor=0 / absolute=0 / escaping=0 / skeleton=0,
    clean. `tools/plan-lint.py CHUNK-D4-SPEC.md`: PASS.
11. chunk-D3-1 §3 three-form exclusion re-run against the 13 newly archived entries: every
    entry × 3 reference forms tested against `evidence/LEDGER.md`, `tests/`, `tools/` →
    39 combinations, 0 hits. Pre-D4-1 zero-reference claim holds post-move.
12. `git log --follow` traces `…/archive/r-drs-role-split-2/grok-4.5.stream.json` through
    `0663444` → `4965f1e` (D2 baseline) → `8f762df`; `planning/pilots/ai-discovery/README.md`
    through `0663444` → `eccf4a7` (file's birthplace).
13. Scope static: `git diff fee5b37..HEAD -- tokens/ evidence/LEDGER.md tests/ …` → empty;
    `git log fee5b37..HEAD --oneline | wc -l` → 1.

## Findings

Both reviewers returned identical-shape nits; all are VERIFIER-PROMPT or
INCIDENTAL-DOC-FIDELITY, none gate action.

- nit (kimi-k3, minimax-m3 — both): `evidence/phase-4.5/build-evidence/r-d2-1-builder-20260814/pre-move-sha256.json`
  lost its trailing newline at EOF in the destinations-only rewrite (fee5b37 ended `}\n`;
  HEAD ends `}`). JSON parses fine (both reviewers' check-5/6 scripts load it without
  warning). Cosmetic. **No gate action.** A one-touch follow-up `printf '\n' >>` restore
  in any later chunk that touches the file would fix it.

- nit (kimi-k3): the verifier prompt listed `ARCHIVE-INDEX.md` as gaining "12 new rows";
  the real number is 13, matching the 13 deferred entries + 13 in the table. **No gate
  action** — committed chunks are correct.

- nit (kimi-k3, minimax-m3 — both): verifier prompt check 10 used `grep -cE '^\| r-'`
  which doesn't match the file's full-path row format (`` \| `evidence/phase-4.5/build-evidence/r-…` ``).
  Underlying claim (27 table rows) verified by `grep -cE '^\\| \`evidence'`. **No gate
  action** — verifier prompt slip, not chunk defect.

- nit (kimi-k3): verifier prompt check 13 expected `pilots/ai-discovery/README.md` `--follow`
  to pass through `ee90061`; `ee90061` (D1 baseline) did not touch `pilots/`. The file's real
  birthplace is `eccf4a7` and the trace correctly reaches it. **No gate action** — verifier
  prompt assumption slip, not chunk defect.

- nit (minimax-m3): the `0663444` commit was amended `--no-edit` to fold in the captured
  `git log --follow` evidence (15 lines confined to `log-follow-representatives.txt`).
  Functionally a snapshot, not a contract, so this is documentation-fidelity only.
  **No gate action.**

None of the nits introduce a defect, security risk, or scope leak. Per `tools/cross_family_review.py:ACCEPT_CLASS`
both reviewers' verdicts are in the ACCEPT-class set, so the gate would pass if invoked.

## Verdict

Both validators independently reproduced every spec exit, byte-identical to the build bundle:

| # | Check (spec §3)                       | kimi | minimax |
|---|---------------------------------------|------|---------|
| 1 | Build summary committed (`0663444`)   | PASS | PASS    |
| 2 | Atomic renames (24, all `0 0`)        | PASS | PASS    |
| 3 | D2 inventory destinations-only update | PASS | PASS    |
| 4 | D2 inventory immutables preserved     | PASS | PASS    |
| 5 | 27 archive entries (14 + 13)          | PASS | PASS    |
| 6 | Three-form post-move scan, 13 new     | PASS | PASS    |
| 7 | `droid-wiki` citations updated        | PASS | PASS    |
| 8 | `PATH-REDIRECTS.md` row + heading     | PASS | PASS    |
| 9 | `ARCHIVE-INDEX.md` 27 entries         | PASS | PASS    |
|10 | `pytest` + wiki-link-audit clean      | PASS | PASS    |
|11 | `git log --follow` retains ancestry   | PASS | PASS    |
|12 | Scope static (single commit)          | PASS | PASS    |

**Combined verdict: ACCEPT-WITH-NITS.** Per `planning/evidence-hygiene/CHUNK-D4-SPEC.md` §5,
the chunk can be merged to `main`. Nits are queued for documentation tidiness; not blocking.

## Process note

Both validators were routed via `tools/run-with-model.sh droid exec --model <id> --auto medium
--cwd /Users/factory/work/adversarial-sprint-dev --output-format json > review-<id>-envelope.json`.
Each envelope captures the full droid exec response as the `result` string. Stderr is captured
separately at `review-<id>-stderr.log` (empty in both cases here — both runs succeeded
cleanly). The per-check "How I verified" tables above paraphrase each envelope's `result`
markdown body.

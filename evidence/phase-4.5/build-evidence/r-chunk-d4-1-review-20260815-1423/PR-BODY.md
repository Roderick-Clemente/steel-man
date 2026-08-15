# [chunk:D4-1] chunk-D4-1: archive deferred 13 entries + relocate pilots/ → planning/

> **PR title to use** (for the GitHub "Open Pull Request" form). The bracketed `[chunk:D4-1]` tag is what `.github/workflows/adversarial-sprint-ci.yml` parses to give the runner a chunk-id. Without it, the workflow bails early on `Determine chunk under review`.

> **Before merging: untick `adversarial-sprint-review/gate` from the `main` branch's required-status checks** (Settings → Branches → main branch protection → "Require status checks to pass before merging"). The runner workflow fails on this repo because GH-hosted `ubuntu-latest` does not ship droid (per workflow file lines 9-13: this is a documented known issue). The substantive cross-family review is already on disk at `evidence/phase-4.5/build-evidence/r-chunk-d4-1-review-20260815-1423/SUMMARY.md` (kimi-k3 + minimax-m3, both ACCEPT-WITH-NITS).

## What

Closes the remaining disk-side cleanup from `planning/evidence-hygiene/PLAN.md`:

- **Archive 13 deferred build-evidence entries** (deferred from chunk-D3-1 — referenced entries restored to flat paths; zero-reference entries left in place). All 13 confirmed zero-reference under the chunk-D3-1 §3 three-form scan (entry, `phase-4.5/build-evidence/<entry>`, `evidence/phase-4.5/build-evidence/<entry>`) against `evidence/LEDGER.md`, `tests/`, `tools/`. Move is byte-identical to D2 inventory's recorded SHA-256.
- **Relocate `pilots/ai-discovery/` → `planning/pilots/ai-discovery/`**. The 4 files (1 README + 3 validator outputs) were always research notes — they sat at the repo top only because they were drafted before the `planning/` folder existed. They are not working pilot slices.
- **Refresh `planning/evidence-hygiene/ARCHIVE-INDEX.md`** to list 27 entries (14 from chunk-D3-1 + 13 from this chunk). Adds an "Archive rule" note explaining the destinations-only D2 inventory rewrite.
- **Append `planning/PATH-REDIRECTS.md` row** for `pilots/` → `planning/pilots/`.
- **Rewrite 3 `droid-wiki` citation lines** in `droid-wiki/findings/first-h1-evidence.md` to point at the new pilot path.

## Diff shape

| Kind | Count | Notes |
|---|---|---|
| Renames (`git mv`) | 24 | 4 pilots + 20 archive; all R100, all `0 0` numstat |
| Non-rename content edits | 4 | `droid-wiki/findings/first-h1-evidence.md` (3 citation lines), `pre-move-sha256.json` (deferred 20 destinations only), `PATH-REDIRECTS.md` (heading + 1 row), `ARCHIVE-INDEX.md` (title + 13 rows + rule note) |
| Build-evidence bundle | 10 files | Tracked under `evidence/phase-4.5/build-evidence/r-chunk-d4-1-builder-20260815-0916/` |

`git diff --find-renames --numstat fee5b37..HEAD` shows 24 `0  0` rename lines + 4 non-zero content edits totalising 28 lines, matching the saved `diff-numstat.txt`.

## Verification

All 12 exits from `planning/evidence-hygiene/CHUNK-D4-SPEC.md §3` green. See `evidence/phase-4.5/build-evidence/r-chunk-d4-1-builder-20260815-0916/` for the build bundle:

| File in bundle | What it proves |
|---|---|
| `CHUNK-D4-SPEC.md` | The spec under which the commit was authored. |
| `PROMPT-D4-BUILDER.md` | The deterministic builder prompt that produced the commit. |
| `pre-move-sha256-all-34.txt` | Pre-move SHA-256 of all 34 inventory destinations. |
| `pre-move-sha256-deferred-20.txt` | Subset for the 20 newly archived (audit-form). |
| `sha-recompute.txt` | Post-move SHA recompute vs D2 inventory: 34/34 verified, 0 mismatches. |
| `pytest.txt` | 241 passed, 3 skipped (the documented `test_layout_paths.py:56` triple). |
| `wiki-link-audit.txt` | Clean (61 pages, dead=0 / anchor=0 / absolute=0 / escaping=0 / skeleton=0). |
| `plan-lint.txt` | PASS — source: none (heuristic mode). |
| `diff-numstat.txt` | 24 `0 0` renames + 4 content edits = 28 lines. |
| `log-follow-representatives.txt` | `git log --follow` traces ancestry through D2 baseline. |

## Review

Cross-family review bundle: `evidence/phase-4.5/build-evidence/r-chunk-d4-1-review-20260815-1423/` (round 1).

| Validator | Family | Verdict | Envelope SHA-256 |
|---|---|---|---|
| kimi-k3 | moonshot/kimi-family | `ACCEPT-WITH-NITS` | `eb99587724ee92862422002bba2d0525202182535bdd606199592968e6229af0` |
| minimax-m3 | minimax/minimax-family | `ACCEPT-WITH-NITS` | `66c4789688f5524ffcefadd0c2d920831e4113d615ef71eb24ccd4435fdb52e9` |

Both nits are cosmetic / prompt-side, NOT chunk defects:

- `pre-move-sha256.json` lost its trailing newline at EOF (JSON parses; restoring `}\n` is a one-byte follow-up if the operator cares).
- Verifier prompt had three prompt-side slips (row-count overcount by 1 in `ARCHIVE-INDEX.md`'s `12` → `13` description, regex pattern in check 10 that didn't match the file's row format, `ee90061` baseline assumption that didn't apply to `pilots/` README in check 13). All three are recorded in the review SUMMARY for future droid context; the commit itself is correct under each check.

See `r-chunk-d4-1-review-20260815-1423/SUMMARY.md` for the full per-check table.

## Risk footprint

- **Single commit on top of fee5b37**. No `tokens/`, no `LEDGER.md`, no `tests/`, no orchestration tooling touched.
- **D2 immutables are the byte-identity contract**: post-move SHA recompute matches the recorded SHA for all 20 newly archived files; the inventory's `canonical_d1_tree` and `tokens` arrays are byte-identical to fee5b37.
- **No deletion semantics**: 4 + 20 = 24 atomic renames, all R100 by `git diff --name-status -M`.

Single-shot merge is safe.

## Suggested merge-button reviewers

`MODEL_FAMILY_MAP` shows `gemini-3.1-pro-preview` (google/gemini-family) and `grok-4.5` (xai/grok-family) as available model families not used in the chunk-D4-1 review pair. Per the chunk-D3-1 close pattern, a merge-button pair from those two families is sufficient to ratify the cross-family verdict.

推荐 merge command: any of `feat:` and `fix:` trigger our standard squash-merge path; suggested merge commit title:

```
chunk-D4-1: archive deferred 13 entries + relocate pilots/ → planning/ (#7)
```

## Build bundle path (in this branch)

`evidence/phase-4.5/build-evidence/r-chunk-d4-1-builder-20260815-0916/`

# Archive Index — chunk-D3-1

Moved entries under `evidence/phase-4.5/build-evidence/archive/` with original path and reason.

| Original path | Reason |
|---|---|
| `evidence/phase-4.5/build-evidence/r-chunk1-builder-verify-20260814` | bootstrap probe |
| `evidence/phase-4.5/build-evidence/r-layout-refactor-20260813-142900` | abandoned layout-refactor draft |
| `evidence/phase-4.5/build-evidence/r-layout-refactor-v2-20260813-2007` | abandoned layout-refactor draft |
| `evidence/phase-4.5/build-evidence/r-layout-refactor-v3-20260813-2048` | abandoned layout-refactor draft |
| `evidence/phase-4.5/build-evidence/r-panel-pass1` | superseded panel pass |
| `evidence/phase-4.5/build-evidence/r-panel-pass2` | superseded panel pass |
| `evidence/phase-4.5/build-evidence/r-panel-pass3` | superseded panel pass |
| `evidence/phase-4.5/build-evidence/r-panel-pass4` | superseded panel pass |
| `evidence/phase-4.5/build-evidence/r-phase45-20260808-234518` | bootstrap probe |
| `evidence/phase-4.5/build-evidence/r-phase45-20260809-000947` | bootstrap probe |
| `evidence/phase-4.5/build-evidence/r-phase45-20260809-170652` | bootstrap probe |
| `evidence/phase-4.5/build-evidence/r-phase45-20260809-171030` | bootstrap probe |
| `evidence/phase-4.5/build-evidence/r-phase45-20260809-171034` | bootstrap probe |
| `evidence/phase-4.5/build-evidence/r-phase45-20260809-171041` | bootstrap probe |

## Deferred entries (kept flat in this chunk)

The following 13 entries have zero references under the sanctioned three-form
scan against `evidence/LEDGER.md`, `tests/`, and `tools/`, but they are listed
in the D2 production inventory (`evidence/phase-4.5/build-evidence/r-d2-1-builder-20260814/pre-move-sha256.json`).
Moving them would break the D2-1 evidence-consolidation tests, which verify that
the 34 D2-relocated files remain at their recorded destinations. They are
therefore deferred to a future chunk that can update the D2 inventory or
re-scope the move under a LEDGER/tests/tools-only rule.

| Path | D2 inventory references |
|---|---|
| `evidence/phase-4.5/build-evidence/r-drs-role-split-2` | 8 files |
| `evidence/phase-4.5/build-evidence/review-convention-gemini-stderr.log` | 1 file |
| `evidence/phase-4.5/build-evidence/review-convention-gemini.json` | 1 file |
| `evidence/phase-4.5/build-evidence/review-convention-grok-stderr.log` | 1 file |
| `evidence/phase-4.5/build-evidence/review-convention-grok.json` | 1 file |
| `evidence/phase-4.5/build-evidence/review-gemini-round2.json` | 1 file |
| `evidence/phase-4.5/build-evidence/review-gemini-stderr.log` | 1 file |
| `evidence/phase-4.5/build-evidence/review-gemini.json` | 1 file |
| `evidence/phase-4.5/build-evidence/review-grok-round2.json` | 1 file |
| `evidence/phase-4.5/build-evidence/review-grok-round3.json` | 1 file |
| `evidence/phase-4.5/build-evidence/review-grok.json` | 1 file |
| `evidence/phase-4.5/build-evidence/rung3-droid-exec-stderr.txt` | 1 file |
| `evidence/phase-4.5/build-evidence/rung3-extract-tool-calls.sh` | 1 file |

## Notes

- All 14 archived entries were verified zero-reference under the three
  sanctioned forms (bare name, `phase-4.5/build-evidence/<entry>`, and
  `evidence/phase-4.5/build-evidence/<entry>`) against `evidence/LEDGER.md`,
  `tests/`, and `tools/` before being moved.
- `r-chunk1-spec-v2-20260813-2114` was restored rather than archived because
  it rests on a single LEDGER attestation row; that single line still counts
  under the brief's explicit three-form criterion, so it stays flat.
- The D2 production inventory was used only as a supplemental cross-check for
  entries that already cleared the LEDGER/tests/tools scan; it did not add any
  exclusion authority on its own. For the 13 deferred entries, however, the D2
  inventory is load-bearing (its tests assert the files still exist at their
  flat paths), so they cannot be archived in this chunk without updating that
  historical artifact.
- A few planning documents cite now-archived paths; those citations are
  historical and expected to be stale after the move (see `evidence/LEDGER.md`
  append-only policy).

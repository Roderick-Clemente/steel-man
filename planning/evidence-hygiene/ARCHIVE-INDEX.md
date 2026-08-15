# Archive Index — chunk-D3-1 + chunk-D4-1

Moved entries under `evidence/phase-4.5/build-evidence/archive/` with
original path and reason.

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
| `evidence/phase-4.5/build-evidence/r-drs-role-split-2` | BURNED, multiple stream/stderr shape |
| `evidence/phase-4.5/build-evidence/review-convention-gemini-stderr.log` | bootstrap probe |
| `evidence/phase-4.5/build-evidence/review-convention-gemini.json` | bootstrap probe |
| `evidence/phase-4.5/build-evidence/review-convention-grok-stderr.log` | bootstrap probe |
| `evidence/phase-4.5/build-evidence/review-convention-grok.json` | bootstrap probe |
| `evidence/phase-4.5/build-evidence/review-gemini-round2.json` | bootstrap probe |
| `evidence/phase-4.5/build-evidence/review-gemini-stderr.log` | bootstrap probe |
| `evidence/phase-4.5/build-evidence/review-gemini.json` | bootstrap probe |
| `evidence/phase-4.5/build-evidence/review-grok-round2.json` | bootstrap probe |
| `evidence/phase-4.5/build-evidence/review-grok-round3.json` | bootstrap probe |
| `evidence/phase-4.5/build-evidence/review-grok.json` | bootstrap probe |
| `evidence/phase-4.5/build-evidence/rung3-droid-exec-stderr.txt` | bootstrap probe |
| `evidence/phase-4.5/build-evidence/rung3-extract-tool-calls.sh` | bootstrap probe |

Total: 27 entries — 14 from chunk-D3-1 + 13 from chunk-D4-1.

## Notes

- All 27 archived entries were verified zero-reference under the three
  sanctioned forms (bare name, `phase-4.5/build-evidence/<entry>`, and
  `evidence/phase-4.5/build-evidence/<entry>`) against `evidence/LEDGER.md`,
  `tests/`, and `tools/` before being moved.
- `r-chunk1-spec-v2-20260813-2114` was restored rather than archived because
  it rests on a single LEDGER attestation row; that single line still counts
  under the brief's explicit three-form criterion, so it stays flat.
- **Archive rule for the 13 chunk-D4-1 entries.** These cleared the
  LEDGER/tests/tools scan but were *load-bearing* in the D2 production
  inventory at
  `evidence/phase-4.5/build-evidence/r-d2-1-builder-20260814/pre-move-sha256.json`.
  chunk-D3-1's round-2 review deferred the move so D2-1's tests
  (`tests/test_evidence_consolidation_d2.py`) would keep passing. chunk-D4-1
  relaxed this by **destinations-only rewriting** of the inventory: every
  affected row's `destination` field was updated from
  `evidence/phase-4.5/build-evidence/<entry>/<file>` to
  `evidence/phase-4.5/build-evidence/archive/<entry>/<file>`. The other
  fields (`source`, `source_file_count=34`, `source_bytes=1410544`,
  per-row `bytes` and `sha256`, `canonical_d1_tree`, `tokens`) are
  byte-identical to pre-chunk-D4-1 state — the inventory remains the
  byte-identity contract for the move.
- A few planning documents cite now-archived paths; those citations are
  historical (recorded under the pre-archive path) and remain in place
  per `evidence/LEDGER.md`'s append-only policy. The single chunk-D4-1
  *living-doc* citation (in `droid-wiki/findings/first-h1-evidence.md`)
  was edited to the new path; everything else (overview/architecture.md,
  overview/by-the-numbers.md, README.md, layout-refactor's CHUNK-3-SPEC.md
  and PLAN.md, `tools/wiki-link-audit.py`'s reads of them) is historical
  and is now covered in `planning/PATH-REDIRECTS.md` only when the
  redirect applies, not when the file itself was rewritten.

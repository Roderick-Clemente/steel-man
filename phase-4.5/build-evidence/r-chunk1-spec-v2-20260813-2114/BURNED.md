# Run `r-chunk1-spec-v2-20260813-2114` — BURNED. Zero verdicts.

**This run produced no review.** Both reviewer invocations terminated before
rendering judgment. The raw envelopes are preserved here as failure evidence,
not as attestations.

> **Do not SHA either file into a chunk-close token, and do not post them as
> `VALIDATE COMPLETE:` / `REVIEW REQUEST:` paths.** A digest over a
> verdict-less envelope is the shape §21 exists to refuse: a real hash of a
> real file that contains no reviewer opinion. Same class as
> `phase-4.5/build-evidence/r-drs-role-split-1/`.

## Provenance

| field | value |
|---|---|
| artifact under review | `planning/layout-refactor/CHUNK-1-SPEC.md` v2 |
| prompt | `spec/PROMPT.md` (same bytes as v1 run, commit ref swapped) |
| repo HEAD at fire time | `d2d89e0` |
| branch | `factory/layout-refactor` |
| droid version | `0.180.0` |
| fired by | builder session in orchestrator seat (§24); no signing key held |
| reviewer models | `kimi-k3`, `minimax-m3` (operator-selected, Droid Core tier) |

## Envelopes

| envelope | model | bytes | is_error | num_turns | session_id | verdict | admissible |
|---|---|---|---|---|---|---|---|
| `spec/kimi-k3.json` | kimi-k3 | 410 | **true** | **0** | `3e74cdb7-27d1-4532-8c93-89e222cde320` | **NONE** | **no** |
| `spec/minimax-m3.json` | minimax-m3 | 302 | **true** | **0** | `360e4baa-96e3-42ac-a55d-84a07b16fb0b` | **NONE** | **no** |

Terminal state, verbatim:

- `kimi-k3.json` — `"subtype":"failure"`, `duration_ms` 74445, result truncated
  mid-reasoning: *"The grep reveals several hits not in the spec's inventory.
  Let me check the phase-\* directories and examine the ambiguous sites more
  closely."* The reviewer was mid-inventory-verification when the session ended.
- `minimax-m3.json` — `"subtype":"failure"`, `duration_ms` 31675, result:
  *"Exec failed"*.

Session ids are distinct and families are distinct, so §17.2 and §23
operational-distinctness would both pass. Neither predicate matters here:
there is nothing to audit. Both envelopes fail the prior question of whether
a review happened at all.

## Cause

Both fires landed inside the builder session's Droid Core 5-hour usage-limit
window (the limit was hit and reset around this period).
`cache_read_input_tokens` was 162820 for kimi and 453551 for minimax — both
sessions had loaded substantial context before terminating, consistent with a
quota/rate termination rather than a prompt or tool-permission defect.

The `--auto low` flag and the read-only tool list (`Read,Grep,Glob,LS`) were
identical to the v1 fire of this same prompt, which completed successfully:
`r-chunk1-spec-20260813-2101/spec/kimi-k3.json` 14123 bytes and
`minimax-m3.json` 16333 bytes, both carrying `VERDICT:` lines. The 410/302
byte envelopes here are ~2.5% of that size.

**Not** an autonomy-tier refusal: no `insufficient permission` error appears in
either envelope, unlike `r-drs-role-split-1`'s grok seat.

## What did NOT happen

The builder did not post these paths to `STEER.md`. No `VALIDATE COMPLETE:` and
no `REVIEW REQUEST:` line cites this run id. The §7 failure mode here would
have been to report "two envelopes on disk, both hashed, session ids distinct"
as though it evidenced two completed reviews — the exact error
`r-drs-role-split-1`'s post-mortem records. The byte counts are in this file
instead.

## Disposition

Re-fire under a fresh run id, **sequentially** rather than in parallel, now
that the usage window has reset. This run id is not reused (per the
`r-drs-role-split-1` precedent). Successor run: `r-chunk1-spec-v3-*`.

Per §5 this is one bounded retry. If the re-fire also burns, the builder
records `BLOCKED: chunk=chunk-D1-1-spec reason=reviewer-burn` and halts the
deliverable rather than proceeding on unreviewed spec.

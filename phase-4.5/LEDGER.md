# Review ledger

**append-only; prior rows immutable per §21**

Tracked, durable record of the review protocol's control lines.
`STEER.md` stays gitignored because it is live control *input* — an
operator writes into it mid-run. This file is the *record*, and it
travels with the repo.

Rows are appended in chronological order. Nothing above the last line
is ever edited: a correction is a new row that cites the row it
supersedes. Row types:

| type | meaning |
|------|---------|
| `VALIDATE COMPLETE` | one reviewer envelope landed; names validator, chunk, envelope path, session_id |
| `REVIEW REQUEST` | builder asks the referee to audit a set of envelopes |
| `REVIEW COMPLETE` | referee's verdict + signed token + envelope sha256s + distinctness metrics |
| `BLOCKED` | a gate could not be satisfied; names the reason |
| `SHA MAP` | maps an envelope path to its sha256 as audited |

## Envelope sha256 map

Recorded because a token attests to *bytes*, and the audit is only
reproducible if the bytes are identified independently of the path.

| envelope | sha256 | verdict |
|----------|--------|---------|
| `phase-4.5/build-evidence/r-chunk1-spec-20260813-2101/spec/kimi-k3.json` | `5da40f618e7948e77f2b0cbba04fe40501bd5b96bfa4faa8346c74b0af8933d1` | REJECT |
| `phase-4.5/build-evidence/r-chunk1-spec-20260813-2101/spec/minimax-m3.json` | `90cdb1b47943c5ebaefd6609edc3c4dcdeb47c15d09e3fab35bb2a2ecd06f1c2` | ACCEPT-WITH-NITS |

## Rows

```
2026-08-13T21:12:47Z BUILDER: VALIDATE COMPLETE: validator=kimi-k3 chunk=chunk-D1-1-spec envelope=phase-4.5/build-evidence/r-chunk1-spec-20260813-2101/spec/kimi-k3.json session_id=09d2e2cf-29f5-48a4-9bcc-90056bc7e9ab
2026-08-13T21:12:47Z BUILDER: VALIDATE COMPLETE: validator=minimax-m3 chunk=chunk-D1-1-spec envelope=phase-4.5/build-evidence/r-chunk1-spec-20260813-2101/spec/minimax-m3.json session_id=274e8c26-8ca1-4e46-97af-9bf4f5b1e68f
2026-08-13T21:12:47Z BUILDER: REVIEW REQUEST: chunk=chunk-D1-1-spec commit=e71487c5feb4ffed60376f6e68cd4508d998fa42 paths=phase-4.5/build-evidence/r-chunk1-spec-20260813-2101/spec/kimi-k3.json,phase-4.5/build-evidence/r-chunk1-spec-20260813-2101/spec/minimax-m3.json ttl=2026-08-14T05:12:47Z artifact=planning/layout-refactor/CHUNK-1-SPEC.md branch=factory/layout-refactor
2026-08-13T22:07:43Z REFEREE: REVIEW COMPLETE: chunk=chunk-D1-1-spec verdict=SPLIT(kimi=REJECT,minimax=ACCEPT-WITH-NITS) token=phase-4.5/tokens/chunk-D1-1-spec.token.json envelope_sha256_kimi=5da40f618e7948e77f2b0cbba04fe40501bd5b96bfa4faa8346c74b0af8933d1 envelope_sha256_minimax=90cdb1b47943c5ebaefd6609edc3c4dcdeb47c15d09e3fab35bb2a2ecd06f1c2 jaccard=0.3910 session_ids_distinct=true commit=6e9a531
```

### Reviews with no admissible envelope

Recorded so the absence is explicit rather than inferred from a gap.

```
2026-08-13T21:14Z BUILDER: BLOCKED: chunk=chunk-D1-1-spec-v2 reason=reviewer-burn run=r-chunk1-spec-v2-20260813-2114 detail=both envelopes is_error/num_turns=0, no VERDICT line; kimi-k3 410 bytes truncated mid-reasoning, minimax-m3 302 bytes "Exec failed"; fired inside a usage-limit window; never posted as attestations; see that run's BURNED.md
```

### Reviews pending a referee ruling

Envelopes exist and carry real verdicts, but no `REVIEW COMPLETE` has
been posted for them yet. Listed here so the outstanding set is
visible rather than tracked only in a session.

```
2026-08-13T22:14Z kimi-k3   chunk=chunk-D1-1-spec-v2 envelope=phase-4.5/build-evidence/r-chunk1-spec-v3-20260813-2140/spec/kimi-k3.json session_id=abdf15aa-3cfb-4fca-8739-59e8c55d2802 verdict=REJECT
2026-08-13T22:30Z grok-4.5  chunk=chunk-D1-1-spec-v3 envelope=phase-4.5/build-evidence/r-chunk1-spec-v4-20260813-2255/spec/grok-4.5.json session_id=ba3487eb-8942-4520-bfa2-bfa4834d0a7c verdict=REJECT
2026-08-13T22:41Z grok-4.5  chunk=chunk-D1-1-spec-v4 envelope=phase-4.5/build-evidence/r-chunk1-spec-v5-20260813-2340/spec/grok-4.5.json session_id=d731517c-2981-4889-b706-aa8bb82e80de verdict=REJECT
```

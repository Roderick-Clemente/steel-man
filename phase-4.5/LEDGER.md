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
| `phase-4.5/build-evidence/r-chunk1-spec-gate-20260814-0000/spec/grok-4.5.json` | `acf05dbd0d9b09cfeaba13cbb1202495e030ddd86156019fe5b5a439177b38f7` | REJECT |
| `phase-4.5/build-evidence/r-chunk1-spec-gate-20260814-0000/spec/gemini-3.1-pro-preview.json` | `60ddbe11d7bbcff15ea88ab66405278bb89b8252053284ef1b90977809168b2b` | REJECT |

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

2026-08-13T23:04:22Z PLANNER: VALIDATE COMPLETE: validator=grok-4.5 chunk=chunk-D1-1-spec-gate envelope=phase-4.5/build-evidence/r-chunk1-spec-gate-20260814-0000/spec/grok-4.5.json session_id=78f9fc48-8a42-484f-9501-cae201cd251f verdict=REJECT prompt_sha256=8c44a29d9b94e2b6971bc7f688d63fca18c4420f6fb9efd4f67ab0fe5861f654
2026-08-13T23:04:22Z PLANNER: VALIDATE COMPLETE: validator=gemini-3.1-pro-preview chunk=chunk-D1-1-spec-gate envelope=phase-4.5/build-evidence/r-chunk1-spec-gate-20260814-0000/spec/gemini-3.1-pro-preview.json session_id=822cab03-1b24-4f91-85d9-b59af65d373b verdict=REJECT prompt_sha256=8c44a29d9b94e2b6971bc7f688d63fca18c4420f6fb9efd4f67ab0fe5861f654
2026-08-13T23:04:22Z PLANNER: REVIEW REQUEST: chunk=chunk-D1-1-spec-gate commit=d3c8005 artifact=planning/layout-refactor/CHUNK-1-SPEC.md artifact_sha256=558f9956a4f029ad23b9c516ce8f49e5035da9e5f220e6f21ebbf5f26998beea paths=phase-4.5/build-evidence/r-chunk1-spec-gate-20260814-0000/spec/grok-4.5.json,phase-4.5/build-evidence/r-chunk1-spec-gate-20260814-0000/spec/gemini-3.1-pro-preview.json ttl=2026-08-14T07:04:22Z branch=factory/layout-refactor note=BOTH-REJECT-cross-family-convergence-on-single-blocker-now-fixed-in-53c75d5

### Errata

Corrections per operator Ruling 4 item 5. Prior rows above are
immutable; these rows supersede specific claims made elsewhere and
name what they supersede.

```
2026-08-13T23:30Z PLANNER: ERRATUM: supersedes=planner-escalation-claim topic=misattributed-reviewer-credit
  CLAIM AS RELAYED (3x, in planner escalations): grok-4.5 credited the §2.2 inventory with
  "zero false positives, zero missed functional sites".
  STATUS: FALSE. Verified: that phrase appears in exactly ONE envelope in this repo,
  r-chunk1-spec-v3-20260813-2140/spec/kimi-k3.json (kimi-k3, NOT grok). No grok envelope
  contains it. Two independent errors: (1) attribution to the wrong family; (2) the
  vocabulary was seeded by the firing seat's own PROMPT.md:40 ("Any site the spec still
  misses? Any false positive?"), so even kimi's phrasing echoes the prompt rather than
  constituting an independent finding. A prompt that supplies the words it wants back
  cannot be cited as corroboration.
  GROK'S ACTUAL WORDS (r-chunk1-spec-gate-20260814-0000/spec/grok-4.5.json, session
  78f9fc48): "Live join/literal sites in §2.2-§2.4 match the repo. Confirmed present:"
  followed by an explicit site list, and "Fenced §2.5 generators and docstring-only sites
  are real and correctly excluded." Grok also states sign_chunk_token.py:135 is a docstring
  Returns: line, not argparse help. That is narrower than the claim it was cited for: it
  confirms the listed sites are real, not that no site is missing.
  IMPACT: the claim was load-bearing in escalations arguing inventory risk was retired.
  It was not. Inventory confidence rests on the mechanical scan and its measured per-file
  counts, not on reviewer praise.

2026-08-13T23:30Z PLANNER: ERRATUM: supersedes=5906a79 topic=verdicts-recorded-in-artifact
  Commit 5906a79 recorded gate verdicts and review history inside
  planning/layout-refactor/CHUNK-1-SPEC.md (site-count paragraph, §2.3 line-number
  paragraph, §2.4 paths.sh paragraph, §2.5 sign_chunk_token paragraph). Verdicts belong
  in this ledger per §21, and a seat recording verdicts into the artifact under its own
  review implicates §22. All such references have been removed from the spec; the
  normative content they carried (the MUST NOT on local_backend.py dirname depth, the
  authoritative-enumeration rule, the paths.sh non-1:1 note) is retained as forward-looking
  requirements with no review provenance.

2026-08-13T23:30Z PLANNER: RETRACTED: rows=3 timestamp=2026-08-13T23:04:22Z reason=Ruling-4-item-4
  The three PLANNER: rows dated 2026-08-13T23:04:22Z (VALIDATE COMPLETE x2 for grok-4.5 and
  gemini-3.1-pro-preview, and REVIEW REQUEST for chunk-D1-1-spec-gate) are RETRACTED as
  improperly seated. CHUNK-1-SPEC is planner-authored, so under Ruling 3 the builder seat
  fires Tier-2 and posts the resulting VALIDATE COMPLETE and REVIEW REQUEST rows. The
  planner firing and recording on its own artifact is the fire-XOR-sign collapse that
  Ruling 2a rejected, and §24 permits a waiver only via an explicit
  "OPERATOR: WAIVE §24 for chunk=<id>" line, which was not issued.
  THE ENVELOPES REMAIN VALID EVIDENCE. They are clean, non-error, on identified bytes
  (commit d3c8005, artifact sha256 558f9956, prompt sha256 8c44a29d), and their sha256s are
  in the map above. What is retracted is the SEATING of the control rows, not the review.
  The builder re-posts these rows under BUILDER: when firing round 7.
```

### Round 7 handoff (pending builder)

Round 7 is the last spec round per Ruling 4 item 3. Bytes to review are
HEAD of `factory/layout-refactor` after the §4.2 restructure, which is
strictly later than the `d3c8005` bytes rounds 5-6 saw. The builder
fires both families, posts `BUILDER: VALIDATE COMPLETE` per envelope and
one `BUILDER: REVIEW REQUEST`, and the referee audits. The planner does
not fire, does not post those row types, and does not sign.

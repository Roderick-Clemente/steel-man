# Cross-family review: Phase 4 Track A/B/C execution outputs

You are reviewing the **execution outputs** of Phase 4 Tracks A, B, and C.
The track *prompts* were already reviewed (post-v3 review, APPROVE-WITH-NITS).
This review covers what was actually **built and committed**.

## What to review

### Track A outputs

1. **`phase-1/scripts/valid-red.py`** — ANSI stripping bug fix. Check:
   - Is the `strip_ansi()` function correct? Does it handle all ANSI escape
     codes that pytest emits?
   - Does the fix change any existing classification behavior (could it
     accept a RED that should be rejected, or vice versa)?
   - Read `phase-1/build-evidence/valid-red-result.txt` — does the evidence
     show the valid RED was correctly accepted and invalid REDs rejected?

2. **`phase-1/fixtures/invalid-red/`** (4 fixture files) — Check:
   - Does each fixture actually trigger the rejection category it claims?
   - Are the fixtures realistic (not strawmanned)?

3. **`phase-4/reconstruct-telemetry.py`** — Check:
   - Does the merge logic correctly deduplicate by run_id?
   - Could it overwrite existing rows?
   - Are the Phase 2 and Phase 3 row extractions accurate against the
     envelopes in `phase-2/build-evidence/` and `phase-3/build-evidence/`?

### Track B outputs

4. **`tools/orchestrate-review.py`** — Hardening changes. Check:
   - Is the stray-write baseline correct (set difference, not set equality)?
   - Is the retry logic sound (retries on 0 output tokens or is_error)?
   - Does the `--treatment` flag correctly exclude `Execute` from validators?
   - Does the adapter shim integration use `to_envelope()` correctly?
   - Are there any new failure modes introduced by the hardening?

5. **`phase-4/h-ci/analysis.md`** and **`phase-4/h-ci/results.json`** — Check:
   - Do the results match the evidence in the per-run envelopes?
   - Is the 27.8% saving calculated correctly?
   - Is the fairness rule check (371 vs 1069 tokens) accurate?
   - Is the quality guard (6/6 ACCEPT both arms) verified?
   - Is the high variance honestly reported?
   - Does the analysis match SPIKE §3.5's outcome definitions?

6. **`phase-4/h3/analysis.md`** and **`phase-4/h3/results.json`** — Check:
   - Was the executor truly un-hinted? Read `phase-4/h3/executor-prompt.md`
     and verify it does NOT contain the solution.
   - Does the diff in `phase-4/h3/executor-diff.patch` show genuine
     implementation (not copied from the prompt)?
   - Is the cross-family validation (grok + gemini ACCEPT) verified?

### Track C outputs

7. **`phase-4/demo/act-1-script.md`** — Check:
   - Do the headline numbers (185k input, 40k output, 594k ms, intervention=1)
     match `tools/RUN-LEDGER.md`?
   - Are the replay commands accurate?

8. **`phase-4/demo/act-2-script.md`** — Check:
   - Is it command-orchestrated (not Mission cosplay)?
   - Is the KI-2 fix (no Execute in bundle mode) stated?
   - Is "close the laptop" honestly handled?

9. **`phase-4/demo/act-3-script.md`** — Check:
   - Does it list ONLY Phase-0-verified controls (Probes 2, 3, 4, 6)?
   - Are Droid Shield, OTel, air-gap listed as roadmap narrative only?
   - Does every claim cite the probe that verified it?

10. **`phase-4/demo/README.md`** — Check:
    - Is the honesty summary accurate (what the demo proves vs does not)?
    - Are the replay instructions complete?

## Grounding documents

- `PRD.md` — the project spec
- `ROADMAP-REVIEW.md` — the v3 review (approved)
- `tools/OPERATING-RULES.md` — operating rules (§7 assert on reality, §16
  demo claims bind to verified capabilities)
- `phase-1/valid-red.md` — valid-RED classifier specification
- `phase-3.2/SPIKE.md` — H-CI experiment design (§3)
- `phase-3.2/BUILD-NOTES.md` — what was built in Phase 3.2
- `tools/RUN-LEDGER.md` — Phase 0.5 cost/latency data
- `tools/PHASE-0.5-CLOSE.md` — Phase 0.5 closure record
- `phase-0/GO-NO-GO.md` — GO-NO-GO decision (command-orchestrated)

## Output format

Emit findings in the PRD §5.3 schema:

```json
{
  "finding_id": "F-TEX-NNN",
  "severity": "blocker|high|medium|low",
  "category": "factual-error|code-bug|honesty-violation|completeness-gap|internal-inconsistency",
  "location": "file:section or file:line",
  "description": "what is wrong",
  "evidence": "quote or citation from grounding doc",
  "recommendation": "what to change"
}
```

End with a verdict: **APPROVE** / **APPROVE-WITH-NITS** / **REJECT**.

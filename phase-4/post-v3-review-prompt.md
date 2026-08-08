# Cross-family review: post-v3 changes (phase renumbering + track prompts)

You are reviewing post-v3 changes to the adversarial sprint framework. The
ROADMAP-REVIEW.md (v3) was already approved by both reviewers. These changes
were made AFTER v3 and have not been independently audited.

## What to review

Read these files and check for factual errors, internal inconsistencies, and
adherence to the project's own rules:

1. **`PRD.md` §11 (Delivery Plan)** — A new Phase 4 (Hardening + roadmap
   review) was inserted after Phase 3.3. Old Phase 4 → Phase 5 (Generalize),
   old Phase 5 → Phase 6 (Hardening settling pass), old Phase 6 → Phase 7
   (Human compression). Check:
   - Are the phase descriptions internally consistent?
   - Do the Track A/B/C/D/E descriptions match ROADMAP-REVIEW.md §4?
   - Are all cross-references updated (e.g., "Phases 0-3" → "Phases 0-4",
     "0-5 arc" → "0-6 arc", "Phase 4" → "Phase 5" in the right places)?
   - Does Phase 7's text correctly reference "Phases 5 and 6" (not "4 and 5")
     in the "Distinct from" paragraph?

2. **`ROADMAP-REVIEW.md` §2 and §4** — Updated to reference new phase
   numbering (Phase 4 = hardening, Phase 6 = old Phase 5, Phase 7 = old
   Phase 6). Check:
   - Does §2 list the correct deferred phases (Phase 6, Phase 7)?
   - Does §4's "Deferred" line match?
   - Are calibration references updated from "Phase 5" to "Phase 6"?

3. **`droid-wiki/overview/index.md`** — Roadmap table updated with all phases
   0-7, current status for each. Check:
   - Are the status descriptions accurate against what was actually built?
   - Is Phase 0.5 shown as "Done" (not "Not started")?
   - Are the wiki story links correct?

4. **`droid-wiki/overview/meta-narrative.md`** — New sections added for Phase
   2, 3, 3.1, 3.2, and 4 (roadmap review). Check:
   - Do the per-phase summaries match the actual phase artifacts?
   - Is the Phase 4 section accurate about the v1 REJECT / v2
     APPROVE-WITH-NITS / v3 final process?

5. **`phase-4/track-{a,b,c}-prompt.md`** — Three standalone execution
   prompts. Check:
   - Do the file paths and script names referenced actually exist?
   - Is Track B's H-CI design consistent with SPIKE §3?
   - Is Track C's Act 3 bounded to Phase-0-verified controls only (no
     Droid Shield/OTel/air-gap)?
   - Are the honesty bounds enforced in each prompt?

## Grounding documents

- `PRD.md` — the project spec
- `ROADMAP-REVIEW.md` — the v3 review (already approved)
- `tools/OPERATING-RULES.md` — operating rules (§7 assert on reality, §14
  run-with-model, §16 demo claims bind to verified capabilities, §17
  model-discipline convention)
- `tools/PHASE-0.5-CLOSE.md` — Phase 0.5 closure record
- `phase-3.2/SPIKE.md` — H-CI experiment design
- `phase-3.2/BUILD-NOTES.md` — what was actually built in Phase 3.2

## Output format

Emit findings in the PRD §5.3 schema:

```json
{
  "finding_id": "F-PV3-NNN",
  "severity": "blocker|high|medium|low",
  "category": "factual-error|internal-inconsistency|rule-violation|missing-reference|scope-creep",
  "location": "file:section or file:line",
  "description": "what is wrong",
  "evidence": "quote or citation from grounding doc",
  "recommendation": "what to change"
}
```

End with a verdict: **APPROVE** / **APPROVE-WITH-NITS** / **REJECT**.

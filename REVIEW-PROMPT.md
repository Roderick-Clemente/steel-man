# Cross-family panel review: ROADMAP-REVIEW.md

You are a **cross-family reviewer** for the Adversarial Sprint project. A
roadmap review has been written by a single-family agent (Factory/Claude). Your
job is to independently audit it and challenge its conclusions. The project's
own thesis is that single-family review is not independence — so this review
needs the same cross-family challenge every other artifact gets.

## What to read

Read these files in the repo at `/Users/factory/work/adversarial-sprint-dev-3.2-build`:

**The artifact under review:**
- `ROADMAP-REVIEW.md` — the full roadmap review (all 5 sections)

**For grounding (read as much as you need to challenge specific claims):**
- `PRD.md` — esp. §11 (delivery plan), §13 (evaluation design), §15 (demo narrative), §17 (model discipline)
- `tools/OPERATING-RULES.md` — esp. §7 (assert on reality), §8 (scope shifts)
- `phase-0/GO-NO-GO.md` — the original GO decision
- `phase-3/README.md` — Phase 3 execution brief (check the exit criteria claims)
- `phase-3.2/BUILD-NOTES.md` — what was actually built in 3.2
- `phase-3.2/SPIKE.md` — the 3.2 spike design (check the H-CI claims)
- `telemetry/runs.jsonl` — the actual telemetry data (check the "no data" claim)
- `tools/orchestrate-review.py` — the orchestration script (check the "never ran" claim)

## What to challenge

### 1. Are the "missed wins" actually missed?

The review claims 10 missed wins (§3.1-3.10). For each one you examine:
- Is the claim **accurate**? Did the review correctly characterize what happened?
- Is the claim **material**? Does it actually matter for the roadmap, or is it noise?
- Did the review **miss** any missed wins that are more important than the ones it listed?

### 2. Is the proposed re-sequencing correct?

The review proposes a 5-priority re-sequencing (§4) that puts "fix the
orchestration loop" first and pushes the Harness backend / 3.3 visual tier /
framework dogfood to last. Challenge this:
- Is fixing orchestration really the highest-leverage next step?
- Is there a sequencing that's better than both the current roadmap AND the proposed one?
- Does the proposed ordering create any **deadlocks** — where a later priority turns out to be a prerequisite for an earlier one?
- Is the "fix foundations before extending" framing correct, or is there an argument for extending first and letting the extensions pull the foundation fixes?

### 3. Did the review miss anything macro?

The review is detailed but was written by one family. Look for:
- **Structural blind spots** — things that are obvious from your family's perspective but were missed.
- **Over-corrections** — did the review overreact to a gap and propose a fix that's worse than the problem?
- **Missing context** — does the review fail to account for constraints (budget, timeline, platform limitations) that should shape the roadmap?
- **Demo strategy** — is the review's treatment of the demo (§4, Priority 4) adequate, or is there a better way to think about what the demo needs to show?

### 4. Are the proposed operating rules (§5, §9-§14) sound?

Six new rules are proposed. For each:
- Is the rule **correct** — does it address a real failure pattern?
- Is the rule **actionable** — can an agent follow it without ambiguity?
- Does the rule **create new problems** — does it over-constrain in a way that slows legitimate work?
- Are there rules that should be added that the review didn't propose?

### 5. What would you sequence differently, and why?

If you disagree with the proposed re-sequencing, propose your own. Be specific
about what goes first, what goes second, and why. If you agree, say so —
confirmation from an independent family is data, not rubber-stamping.

## Output format

Emit findings in the PRD §5.3 schema:

```json
{
  "id": "F-RR-001",
  "severity": "blocker|high|medium|low",
  "category": "factual|semantic|scope|sequencing|process|omission",
  "section": "ROADMAP-REVIEW.md §X.Y",
  "claim": "what the review says that you challenge or supplement",
  "evidence": ["path:line or specific observation"],
  "recommended_change": "what should change",
  "risk_if_ignored": "what happens if this is not addressed"
}
```

End with an overall verdict:
- **APPROVE** — the review is sound; no material changes needed.
- **APPROVE-WITH-NITS** — the review is directionally correct; findings are improvements, not corrections.
- **REJECT** — the review has a material flaw that changes the roadmap conclusion.

Be honest. If the review is good, say so — false disagreement is as useless as false agreement. If the review missed something important, name it with evidence. The goal is a better roadmap, not a louder argument.

# Adversarial review pass — findings log

This is the build session's structural + cross-perspective
adversarial review pass. Real model-mediated cross-family review
is KNOWN-ISSUES.md §KN1's named gap. Each finding below carries a
stable finding_id, severity, category, lens (which perspective
raised it), and a disposition.

The `findings.jsonl` / `dispositions.jsonl` files are git-ignored
per PRD §17.4. The schema lives at `telemetry/SCHEMA.md`. This
file is the **markdown** mirror of those rows for readability +
auditability of *this branch* — committed so reviewers can read
without re-running the aggregator.

## Findings

```
F-PRD-001 | medium | scope          | PRD-strict    | commit_chunk_change stages framework-side evidence dir, not pilot-side mutations
F-PRD-002 | low    | ergonomics     | PRD-strict    | reconcile packet shows "round 2 / max 2" on first reconcile (cosmetic)
F-PRD-003 | medium | dry-run        | PRD-strict    | plan-reviewer verdict UNKNOWN on dry-run envelopes (handled in packet)
F-DX-001  | medium | ergonomics     | pragmatic-DX  | CLI surface is wide (~30 flags); config-file-first iteration needed
F-DX-002  | low    | ergonomics     | pragmatic-DX  | per-chunk status banner is the only log stabilizer
F-DX-003  | medium | ergonomics     | pragmatic-DX  | --non-interactive without --dry-run is implicit but documented
F-SEC-001 | high   | kiwi-2 (closed)| security-skeptic | LocalBackend hardcodes validator --enabled-tools (KI-2 preventive fix is THIS)
F-SEC-002 | medium | signing-key    | security-skeptic | operator env-var re-set mid-run is not modelled (out of scope)
F-SEC-003 | low    | concurrency    | security-skeptic | parallel-runner race on same machine (out of scope)
```

## Dispositions

| finding_id | disposition | rationale |
|---|---|---|
| F-PRD-001 | accepted | commit body line "Gate: ACCEPT" already names what was committed; more verbose body is a future-dx win |
| F-PRD-002 | accepted | KNOWN-ISSUES.md KNE2 cosmetic; sed fix can land in any chunk |
| F-PRD-003 | accepted | reconcile packet shows "0 findings — clean null per PRD §13" — explicit |
| F-DX-001 | accepted | RUN-PROMPT.md shows --config file-only invocation; future simplification can rely on a JSON-only mode |
| F-DX-002 | accepted | banner + per-chunk event sounds are operator's territory (Phase 7) |
| F-DX-003 | accepted | documented; help text; KNOWN-ISSUES names it |
| F-SEC-001 | accepted-no-fix | §17.5 refuses-by-construction on validators' Execute; widening would re-open the KI-2 vector |
| F-SEC-002 | accepted-no-fix | Phase 3.2 SP/ke1 fix already established the right shape |
| F-SEC-003 | accepted-no-fix | parallel-runner on same machine is out-of-scope; runner is foreground |

## Stage-A summary numbers

- **9 findings** raised across three lenses.
- **0 blockers.**
- **3 disposition = accepted no-fix** (structural decisions).
- **6 disposition = accepted with note / future-dx win**.
- **0 disposition = rejected** (no finding was overturned; lenses applied sharply).

Real droid-mediated cross-family review (Stage B) is the
follow-on — see KNOWN-ISSUES.md §KN1 / §KN2.

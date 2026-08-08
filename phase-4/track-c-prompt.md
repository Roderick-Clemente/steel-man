# Phase 4, Track C — Demo honesty

You are executing **Phase 4 Track C** of the adversarial sprint framework. This
track packages the demo narrative with strict honesty bounds. It overlaps
Track B after B1 (orchestration hardening) is done — Act 2 needs the hardened
orchestrator. Act 1 and Act 3 do not.

## Context

The project is at `/Users/factory/work/adversarial-sprint-dev-3.2-build`. The
pilot repo is at `/Users/factory/work/quantum-bank--llms-txt-pilot`. Read
`ROADMAP-REVIEW.md` for the full project audit. Read `PRD.md` §15 for the demo
spec. Read `tools/PHASE-0.5-CLOSE.md` for Act 1 substance.

## The core principle

**Demo claims bind to verified capabilities.** The OPERATING-RULES §16 rule
says: "don't demo what you haven't built." The v1 roadmap review violated this
by listing Droid Shield, OpenTelemetry export, and air-gapped deployment in
Act 3 — none of which were verified by Phase 0 probes. This track enforces the
rule.

## Acts

### Act 1 — The manual baseline (packaged by Track A)

Act 1 is the Phase 0.5 manual baseline harness. The substance exists
(`tools/PHASE-0.5-CLOSE.md` — headless real runs, blind validators,
cost/latency/intervention logging, fake-pass regression fixture). Track A
packages it as `phase-4/demo/act-1-script.md`.

**If Track A has not completed:** package Act 1 yourself using
`tools/PHASE-0.5-CLOSE.md`, `tools/RUN-LEDGER.md`, and `tools/REPRODUCE.md`.
The script should state what Act 1 demonstrates, list the concrete commands,
show expected output, and state the headline numbers (185k input tokens, 40k
output tokens, 594k ms wall-clock, operator-intervention = 1).

**Honesty bound:** Act 1 is the honest comparison arm. It is NOT the plugin.
It is the best achievable with two CLIs and shell. If it turns out to be
nearly as good as the plugin, that is a finding worth having before a demo
rather than during one (PRD §11 Phase 0.5).

### Act 2 — The command-orchestrated loop

**Problem:** PRD §15 describes Act 2 as "same sprint as a Mission." But the
GO-NO-GO decision was command-orchestrated — Mission-native is closed
(`droid exec --mission` is a no-op that reports success, Probe 1). The demo
must not cosplay a Mission. "Push a scripted button" is the honest version.

**Steps:**

1. **Wait for Track B step B1** (orchestration hardening). Act 2 needs a
   working orchestrator. If B1 is not done, start with Act 3 instead.

2. **Write the demo script** as `phase-4/demo/act-2-script.md`:
   - State what Act 2 demonstrates: the full adversarial loop running
     end-to-end via `orchestrate-review.py`, not a Mission.
   - List the concrete command: `python3 tools/orchestrate-review.py ...`
     with the actual parameters (pilot repo, locked test, validators).
   - Show the expected flow: produce evidence bundle → run N validators →
     check stray writes → parse verdicts → append telemetry → report gate
     decision.
   - **Preventive KI-2 in the demo:** in bundle-consuming mode, validators
     don't get `Execute` tool. This is the Evidence Provider fix
     (ROADMAP-REVIEW §3.13), demonstrated live. State this explicitly.
   - Show the expected output: ACCEPT from both validators, telemetry row
     appended, gate decision = PASS.

3. **Honesty bounds:**
   - No Mission cosplay. The command is a script, not a Mission.
   - "Close the laptop" requires a demonstrated durable runner that has
     NOT been evidenced. Either build one (out of scope for this track) or
     drop the claim. Do NOT demo autonomy that hasn't been evidenced.
   - If the orchestrator still has flakiness (ERROR/UNKNOWN rows), show it
     honestly. The retry logic from B1 should handle most cases, but if a
     run fails, show the failure and the retry — don't hide it.

### Act 3 — Phase-0-verified controls only

**Problem:** The v1 roadmap review listed Droid Shield, OpenTelemetry export,
and air-gapped deployment as demo capabilities. NONE of these were verified by
Phase 0 probes. This violates OPERATING-RULES §16.

**Steps:**

1. **Write the demo script** as `phase-4/demo/act-3-script.md`:
   - State what Act 3 demonstrates: the Phase-0-verified platform controls.
   - List ONLY capabilities that were actually verified by Phase 0 probes:
     - **Model pinning** (Probe 2): `--model` pins resolve exactly, invalid
       ID fails closed at exit 1.
     - **Hook enforcement** (Probe 4): a `PreToolUse` hook blocks the
       executor's edit and the run continues on the refusal.
     - **Context isolation** (Probe 3): tool restrictions on a custom agent
       are genuinely enforced (but transcript is readable off disk — the
       guard must block those paths).
     - **Plugin scaffold** (Probe 6): droid, skill, and hook ship as a
       single install.
   - For each capability, show the probe command and the observed result.
   - **What is NOT in Act 3** (list as roadmap narrative, not demo claims):
     - Droid Shield — NOT verified. Roadmap narrative until re-probed.
     - OpenTelemetry export — NOT verified. Roadmap narrative until
       re-probed.
     - Air-gapped deployment — NOT verified. Roadmap narrative until
       re-probed.

2. **Honesty bounds:**
   - Every claim in Act 3 must cite the probe that verified it.
   - Unverified capabilities are listed as "roadmap narrative" with a note
     that they require re-probing before they can be demoed.
   - Do not imply capabilities that have not been tested.

## Demo assembly

After all three acts are packaged, create `phase-4/demo/README.md`:

1. **Narrative arc:** Act 1 (baseline) → Act 2 (the loop, command-orchestrated)
   → Act 3 (verified controls). State the story: "here is what the method does,
   here is what it costs, here is what the platform enforces."

2. **Honesty summary:** what the demo proves and what it does not.
   - Proves: the loop runs end-to-end, cross-family validation works, the
     evidence provider saves tokens (if H-CI is done), the platform enforces
     the core invariants.
   - Does not prove: autonomy ("close the laptop"), Droid Shield, OTel,
     air-gap, or anything not verified by Phase 0 probes.

3. **Replay instructions:** how to run each act from a clean checkout.

## Operating rules

- Read `tools/OPERATING-RULES.md` before starting. Follow all rules.
- Demo claims bind to verified capabilities (§16). If you can't cite the
  probe that verified it, it doesn't go in the demo.
- No Mission cosplay (GO-NO-GO decision). Act 2 is command-orchestrated.
- "Close the laptop" requires a durable runner. Either build one or drop
  the claim. Do not demo autonomy that hasn't been evidenced.
- Commit each act's script as a separate commit with a clear message.

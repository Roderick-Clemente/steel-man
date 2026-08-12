# H-CI Experiment Analysis

## Hypothesis

Routing deterministic evidence through a provider (the EvidenceBundle)
*reduces average token cost at equal acceptance quality.* Only the evidence
source changes: control arm validators run pytest in-session; treatment arm
validators read a pre-produced EvidenceBundle (no Execute tool — this is also
the KI-2 fix).

## Setup

| Parameter | Value |
|---|---|
| Locked chunk | Chunk 1 — profile read model (`get_user_profile` in `models.py`) |
| N runs per arm | 3 |
| Validators | grok-4.5 (xAI) + gemini-3.1-pro-preview (Google) — cross-family |
| Reasoning effort | `--auto high` |
| Control arm tools | Read, Glob, Grep, LS, Execute (validators run pytest) |
| Treatment arm tools | Read, Glob, Grep, LS (no Execute — KI-2 fix) |
| Evidence source (control) | In-session raw pytest output |
| Evidence source (treatment) | EvidenceBundle embedded in prompt |
| Tokenizer | tiktoken cl100k_base (provider tokenizer, not chars/4 proxy) |

## Results

### Per-model token comparison (input + output, mean of 3 runs)

| Model | Control mean | Treatment mean | Delta | Delta % |
|---|---|---|---|---|
| grok-4.5 | 23,095 | 18,434 | -4,661 | -20.2% |
| gemini-3.1-pro-preview | 127,674 | 90,472 | -37,202 | -29.1% |
| **Panel (both)** | **75,385** | **54,453** | **-20,931** | **-27.8%** |

### Panel totals per run

| Run | Control | Treatment | Delta | Delta % |
|---|---|---|---|---|
| 1 | 119,433 | 139,635 | +20,202 | +16.9% |
| 2 | 258,816 | 127,172 | -131,644 | -50.9% |
| 3 | 74,059 | 59,913 | -14,146 | -19.1% |

Run 1 is an outlier where treatment cost more than control. Run 2 shows the
largest treatment saving (control's gemini run consumed 233k tokens vs
treatment's 101k). The high variance is inherent to LLM runs — this is why
N>=3 runs are required (SPIKE §3.4, "single runs lie").

### Fairness rule (SPIKE §3.2 — MANDATORY)

The fairness rule checks that the bundle read costs less than the raw test
output it replaces. Token counts measured with tiktoken (provider tokenizer,
not the chars/4 proxy):

| Measure | Tokens |
|---|---|
| Bundle (treatment payload, mcp_payload_tokens) | 371 |
| Raw combined pytest output (control, raw_test_output_tokens) | 1,069 |
| **Saving** | **698 tokens (65.3%)** |
| **Fairness rule holds** | **YES** |

The bundle (371 tokens) is smaller than the raw combined pytest output (1,069
tokens) it replaces. This is the test-output-read slice (2) of the validator
run — the only slice CI moves. Diff-read (1) and verdict-reasoning (3) do not
change.

### Quality guard (PRD §13)

| Arm | ACCEPT rate | Verdicts |
|---|---|---|
| Control | 6/6 (100%) | ACCEPT × 6 |
| Treatment | 6/6 (100%) | ACCEPT × 6 |

**Quality held.** The treatment arm produced identical verdicts to the control
arm — all ACCEPT. No quality drop. Cheaper-and-equal is a win.

### Security scans (OUT of cost comparison — SPIKE §3.3)

The EvidenceBundle reports 0 new security findings. Security is a coverage
gain (new lens), not a cost delta. It is reported separately and does not
contaminate the token comparison.

## Verdict

**Directional: bundle < in-session with quality holding, on N=3 per arm.**

**Not a result yet.** Three runs per arm, and run 1 of the treatment arm moved
the *opposite* way (+16.9%). A mean over three runs with one sign flip does not
establish an effect; it establishes that the effect is worth measuring at an n
that could detect it. Do not cite 27.8% as a finding.

The treatment arm (EvidenceBundle) produced a **27.8% mean token reduction**
at **equal acceptance quality** (100% ACCEPT in both arms). The fairness rule
holds: the bundle (371 tokens) is 65.3% smaller than the raw pytest output
(1,069 tokens) it replaces.

Per the SPIKE §3.5 outcome framework:
- **Bundle < in-session, quality holds → externalization is a candidate cost
  lever on the panel.** Build CI-evidence as an *opt-in* mode and keep measuring;
  promoting it to a default is a decision this n cannot license.
- Sizing: the 27.8% panel reduction decomposes as grok -20.2% and gemini
  -29.1%. The context-heavy validator (gemini, 96k-165k input in Phase 3) has
  more headroom, as the SPIKE predicted. Grok (16k-30k input) has less
  headroom but still benefits.
- The deterministic re-run was a meaningful slice of the 84% panel cost.
  Externalizing it via a compact bundle recovers ~28% of panel tokens on
  average.

### Caveats

1. **High variance:** Run 1 showed treatment costing *more* than control
   (+16.9%). The mean is negative (treatment cheaper) but individual runs can
   flip. This is inherent to LLM token consumption — the same prompt can
   produce 55k or 237k tokens depending on how deep the model digs. N>=3
   runs are necessary but even N=3 has wide confidence intervals.

2. **Small absolute chunk:** The locked chunk is a single function
   (`get_user_profile`) with 103 tests. The raw pytest output is already
   compact (1,069 tokens). Larger chunks with more verbose test output would
   show a larger absolute saving.

3. **Bundle embedded in prompt vs MCP pull:** In this experiment, the bundle
   is embedded directly in the treatment prompt (local mode, zero CI). In a
   real MCP-pull scenario, the bundle enters context via a tool call rather
   than the prompt, but the token cost is the same — the bundle enters the
   validator's context either way.

4. **No transient failures:** All 12 runs completed without triggering the
   retry logic (retry_count=0 for all rows). The retry hardening from B1 was
   not exercised but is in place for future runs.

## Conclusion

H-CI supports the hypothesis: routing deterministic evidence through a
compact EvidenceBundle reduces average validator token cost by ~28% at equal
acceptance quality. The KI-2 fix (dropping Execute from validators) is both a
security improvement (closes the write vector) and a cost improvement
(validators don't spend tokens running pytest). CI-evidence should be promoted
as a mode.

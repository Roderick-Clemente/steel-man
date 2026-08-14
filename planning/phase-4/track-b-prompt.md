# Phase 4, Track B — Orchestration harden → H-CI → H3

You are executing **Phase 4 Track B** of the adversarial sprint framework. This
track is the **serial economic fork** — the steps within it must run in order,
but the track does not block Track A or Track C (except that Track C's Act 2
needs the hardened orchestrator from step B1).

## Context

The project root is the repository containing `PRD.md` (this file's parent
directory). The pilot repo is at `/Users/factory/work/quantum-bank--llms-txt-pilot`.
Read `ROADMAP-REVIEW.md` for the full project audit. Read `PRD.md` for the spec.
Read `phase-3.2/SPIKE.md` for the H-CI experiment design. Read
`phase-3.2/BUILD-NOTES.md` for what was built.

## Steps (serial)

### B1. Harden orchestration just enough for N identical runs

**Problem:** `tools/orchestrate-review.py` ran with partial success — 12
telemetry rows in `runs.jsonl`, 10 from orchestrated runs. But it has
residual flakiness: ERROR/UNKNOWN verdict rows (gemini returning 0 tokens on
some runs) and a non-hermetic stray-write check that STOPs on pre-existing
dirty-tree paths (false positive, not validator mutation of product code).

**What to fix (days, not a program — bound to the minimum needed for
credible N-run A/B):**

1. **Use the adapter shim + `run-with-model.sh`** instead of raw parsing /
   direct `DROID_BIN`. The script currently calls `DROID_BIN` directly. It
   should use `tools/adapters/factory.py` (the vendor-neutral envelope
   shim) and `tools/run-with-model.sh` (the enforcement wrapper that refuses
   to run without `--model`). This is OPERATING-RULES §14.

2. **Add stray-write baseline.** The current stray-write check compares
   `git status --porcelain` before and after a validator run and STOPs if
   anything changed. But if the working tree is already dirty (untracked
   files, modified files from prior work), it false-positives. Fix: capture
   a baseline of dirty paths before the run and only flag paths that are
   newly dirty after the run (set difference, not set equality).

3. **Add transient retry logic for provider API failures.** The
   ERROR/UNKNOWN rows are caused by gemini returning 0 tokens on some runs
   (provider API hiccup, not a code bug). Add a retry wrapper: if a
   validator run returns 0 output tokens or an ERROR verdict, retry up to
   2 times with a short delay. The script already catches
   `JSONDecodeError` for empty/malformed envelopes — the missing feature is
   retry, not better error handling.

4. **Make multi-run deterministic.** Same inputs → same outputs. The script
   should be runnable N times with identical parameters and produce
   comparable telemetry rows (same models, same prompts, same diff, same
   evidence). The only thing that should vary is transient API failures
   (which the retry logic handles).

5. **Keep the telemetry append path that already works.** The script
   already appends to `telemetry/runs.jsonl`. Do not break this.

**What NOT to do:**
- Do not gate H-CI on demo packaging or full KI-2 redesign.
- Do not rewrite the script from scratch. Fix the specific issues above.
- Do not add features beyond what N-run A/B needs.

**Exit:** `orchestrate-review.py` can be run N times with identical
parameters and produce comparable telemetry rows. No false-positive STOPs
from dirty-tree paths. Transient API failures are retried. The adapter shim
and `run-with-model.sh` are used. Evidence: run the script 3 times with the
same parameters and show the telemetry rows are comparable.

### B2. Run the H-CI experiment

**Hypothesis (H-CI):** routing deterministic evidence through a provider (the
EvidenceBundle) *reduces average token cost at equal acceptance quality.*
Phase 3 = control arm (in-session raw pytest output); 3.2 = treatment arm
(bundle). **Only the evidence source changes.**

**Design (from SPIKE §3):**

1. **Same locked chunk:** the `/profile` model chunk (chunk 1) from the
   pilot repo. Same commit, same diff, same locked test
   (`test/test_profile_model.py`), same lock manifest.

2. **Same models/prompts:** same validator models (grok-4.5 +
   gemini-3.1-pro-preview), same reasoning effort, same review prompt.

3. **Two arms:**
   - **Control arm (in-session):** validators get `Execute` tool, run pytest
     themselves, read raw output. This is the Phase 3 configuration.
   - **Treatment arm (bundle):** validators get the EvidenceBundle (no
     `Execute` tool needed — they read the bundle). This is the Phase 3.2
     configuration. **This is also the KI-2 fix** — dropping `Execute`
     from validators preventatively closes the write vector.

4. **Parameterize the KI-2 fix:** the orchestrator must support both arms.
   In treatment mode, validators' `--enabled-tools` excludes `Execute`. In
   control mode, it includes `Execute`. This is a flag, not a redesign.

5. **Fairness rule (MANDATORY):** count the bundle read tokens on the
   treatment side. The bundle enters the validator's context and costs
   input tokens. The win is real **only if**
   `tokens(bundle read) < tokens(in-session raw test output it replaces)`.
   Use `phase-3.2/evidence/token_accounting.py` to measure this.

6. **Run N times** (N >= 3). Single runs lie — the same discipline as Phase
   3.1. Use the hardened orchestrator from B1.

7. **Use provider tokenizers** for exact token counts, not the chars/4
   heuristic. The heuristic is a proxy; the experiment needs real numbers.

8. **Security scans stay OUT of the cost comparison** (SPIKE §3.3). Security
   is a coverage gain, not a cost delta. Report security findings separately.

9. **Quality guard:** acceptance-pass-rate must not drop. Cheaper-but-worse
   is not a win (PRD §13). If the treatment arm produces different verdicts
   than the control arm, that is a finding, not a failure — but it must be
   reported.

**What each outcome means (SPIKE §3.5):**
- **Bundle < in-session, quality holds:** externalization is a real cost
  lever. Promote CI-evidence as a mode. Size how much of the 84% panel cost
  was deterministic-re-run vs irreducible review.
- **Bundle >= in-session (or quality drops):** the deterministic re-run was
  not the expensive part — the review reasoning is. A null result is valid
  data (PRD §13). The bigger lever is panel size / validator context
  discipline.

**Output:**
- `phase-4/h-ci/results.json` — per-run telemetry: arm, validator, tokens
  (input/output/cache_read/thinking), verdict, duration.
- `phase-4/h-ci/analysis.md` — summary: mean tokens per arm, delta,
  fairness-rule check, quality guard, verdict.
- Append rows to `telemetry/runs.jsonl` with `evidence_source` field set to
  `local_bundle` (treatment) or `in_session` (control).

**Exit:** H-CI has been run N times, results are on disk, the analysis
states whether the bundle saves tokens and whether quality held.

### B3. Run an H3 validation

**Hypothesis (H3):** a cheap-tier executor can implement a bounded chunk
without being handed the exact fix — the prompt describes the problem, not
the solution. This is the primary cost-saving mechanism of the sprint method
(expensive planning + cheap execution).

**Problem:** In Phase 3, the executor was handed the exact fix (the prompt
contained the solution). This means Phase 3 did not actually test H3. The
cost thesis depends on cheap executors being able to implement from a spec,
not from a solution.

**Design:**

1. **One genuine, un-hinted executor chunk.** Take the `/profile` model
   chunk (or a new chunk of similar scope). Write an executor prompt that
   describes the *problem* (what the behavior should be, what the test
   asserts) but NOT the *fix*. For the /profile chunk, the prompt should
   describe the profile key-set contract (what fields the endpoint should
   return) without giving the implementation. Do NOT use the Phase 1
   charset fix as the example — that is a different slice with a different
   lock file.

2. **Same locked test.** The test is already locked from Phase 1. The
   executor must make it pass without seeing the test source (test
   authorship is independent per invariant #3).

3. **Cheap-tier executor.** Use a cheap model (e.g., `gpt-5.4-mini` or
   `glm-5.2`). This is the seat that's supposed to be safe because the
   plan + test + validation have already been done by more expensive
   models.

4. **Same validation.** Run the hardened orchestrator (B1) with
   cross-family validators (grok + gemini). The validators see the spec,
   the diff, and the evidence — not the executor's reasoning.

5. **Record:** did the cheap executor succeed? How many turns? How many
   retries? How many tokens? Did the validators accept or reject?

**Output:**
- `phase-4/h3/results.json` — executor model, turns, tokens, verdict,
  retry count, duration.
- `phase-4/h3/analysis.md` — did the cheap executor implement from spec?
  What does this say about the cost thesis?

**Exit:** H3 has been run, results are on disk, the analysis states whether
a cheap executor can implement from a spec (the primary cost-saving
mechanism).

## Operating rules

- Read `tools/OPERATING-RULES.md` before starting. Follow all rules.
- Assert on reality, never on exit code (§7).
- Use `run-with-model.sh` for every `droid exec` invocation (§14).
- A clean null result is valid data (PRD §13). Do not manufacture
  disagreement to make the experiment look more interesting.
- Commit each step's output as a separate commit with a clear message.
- If the orchestrator hardening (B1) reveals deeper issues, document them
  but do not expand scope — fix what's needed for N-run A/B, nothing more.

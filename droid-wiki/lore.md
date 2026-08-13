# Lore

A timeline of how the adversarial-sprint framework evolved, from conception to the current state. Derived from git commit timestamps and file creation dates.

## Eras

### Era 1: Conception and feasibility (Aug 3-5, 2026)

The project began as a PRD (`PRD.md`) defining a multi-model adversarial workflow for agentic coding. The core thesis: quality comes from structural separation of roles across different model families, not from a smarter model.

Phase 0 ran seven feasibility probes against the Factory platform:
- Model pinning, fallback safety, context isolation, hook blocking, plugin boundary, self-declared risk
- Each probe could kill or reshape the design
- Key finding: hook blocking was unreliable (the "silent green" defect), but model pinning and context isolation worked

Phase 0.5 extended this into a "rung ladder" of incremental tests, culminating in a fake-pass detection run (rung 5.5) that proved the method could catch a model claiming success while doing nothing.

**Key files created:** `PRD.md`, `phase-0/`, `tools/fixtures/rung*-gate.py`, `tools/adapters/factory.py`

### Era 2: Test-evidence foundation (Aug 5-6, 2026)

Phase 1 built the first vertical slice: a locked behavioral test, an executor that cannot touch it, and a GREEN verifier that checks both the test hash and the asserted reason.

Three scripts were created that remain load-bearing today:
- `phase-1/scripts/lock.py` — hash-lock a test file so it cannot be modified
- `phase-1/scripts/valid-red.py` — verify tests fail for the right reason (not a syntax error)
- `phase-1/scripts/verify-green.py` — re-check the hash, run pytest, refuse GREEN on mismatch

The QuantumBank pilot repo was chosen as the execution target. A doubled-charset bug in `/llms.txt` was found and fixed during this phase.

**Key files created:** `phase-1/scripts/`, `phase-1/locks/`, `tools/run-with-model.sh`

### Era 3: Convention and model discipline (Aug 6, 2026)

The §17 model discipline section was added to the PRD, establishing:
- Every `droid exec` invocation records its resolved model (attribution)
- Separation-bearing seats (validator, reviewer) must pin `--model` before the run (enforcement)
- Telemetry is split: schema and code are public, data rows are gitignored

Cross-family review of the conventions themselves caught real issues: Grok and Gemini both REJECTED the first draft of the hook, forcing fixes for MultiEdit bypass, token-first guards, and structural glob heuristics. This was the method eating its own dog food for the first time.

The `tools/conventions/model-discipline.md` document and `telemetry/SCHEMA.md` (v1) were created.

**Key files created:** `tools/conventions/`, `telemetry/SCHEMA.md`, `telemetry/aggregate.py`

### Era 4: Planning slice and approval (Aug 6-7, 2026)

Phase 2 drafted an adversarial planning brief for a read-only `GET /profile` feature on QuantumBank. The plan went through cross-family review (Grok + Gemini), was revised based on round-1 feedback, and reached APPROVE from both reviewers.

The human plan-approval gate was passed, with the plan hash-bound to `sha256:72eccff5...`. This was the first time the full plan → review → approve cycle ran end-to-end.

**Key files created:** `phase-2/APPROVAL.md`, `phase-2/brief-v2.md`

### Era 5: The execution sprint (Aug 7, 2026)

Phase 3 ran the full adversarial sprint on the approved plan: three chunks (profile read model, route + template, demo seed identity), each going through test-authorship → lock → valid-RED → executor → cross-family validation.

Key events:
- The OpenAI executor seat (gpt-5.4-mini) was unavailable (KI-1), forcing a substitution to glm-5.2 (zhipu). The human approved the swap, preserving family separation.
- All three chunks reached cross-family ACCEPT (grok-4.5 + gemini-3.1-pro-preview, 0 findings on chunk 1).
- The full suite hit 103 tests green. Telemetry captured 29 rows across all role invocations.
- The §17.1 amendment (attribution vs enforcement) was refined and merged during this phase.

This was the first complete run of the method on a real feature, proving the full loop works.

**Key files created:** `phase-3/`, `phase-3/prompts/`, `phase-3/RUN-COMMANDS.md`, `phase-3/gen-telemetry.py`

### Era 6: The degraded loop spike (Aug 7, 2026)

Phase 3.1 tested what happens when the test-author family invariant is degraded — moving the test-author to the executor's own family (glm-5.2).

The result was panel-dependent, not a clean pass/fail:
- The same-family author encoded a test-independence defect in 1 of 3 chunks (a locked test that passed only inside full-suite ordering)
- The deterministic gate caught it every time (standalone execution)
- The panel split: grok-4.5 returned REJECT_TEST; gemini-3.1-pro-preview returned ACCEPT on the same failure
- A single-model gate would have shipped the defect

This produced PRD §17.6: degrading the test-author family invariant is an outage fallback, not a cost lever. The combination of deterministic gate + fail-closed >=2-family panel + retry-on-reject is the recommended hardening for every run.

**Key files created:** `phase-3.1/RESULTS.md`, `phase-3.1/SPIKE.md`, PRD §17.6 amendment

### Era 7: Evidence externalization and orchestration (Aug 7-8, 2026)

Phase 3.2 attacked the 84% problem: validators were 84% of the total token cost in Phase 3, and much of that was re-running pytest and reading raw stdout. The solution: externalize the deterministic tier into a compact signed EvidenceBundle that validators consume instead of re-running tests.

Key events:
- The SPIKE and RECOMMENDATION were written as a plan-only handoff, then human-approved
- The local backend was built: runs pytest + verify-green.py + Bandit ONCE, produces a 919-byte signed JSON bundle
- The validator and orchestrator consumers read the bundle instead of re-running pytest
- Token accounting proved the fairness rule: bundle (229 tokens) < combined raw output (511 tokens) = 55.2% saving on the test-output-read slice

The orchestration gap was discovered during this phase: the review process was ad hoc, run by an AI agent manually executing commands. This led to building `tools/orchestrate-review.py` — the mechanical review pipeline that was missing since Phase 3. The script runs the full cycle (produce evidence → call validators → check stray writes → parse verdicts → append telemetry → report gate) with no asking, no waiting.

Three rounds of cross-family review caught 8 real issues:
1. Forgeable default HMAC key → fixed (random key if env not set)
2. Wrong bandit scope label ("diff" for whole-tree scan) → fixed to "history"
3. Missing cross-family enforcement in orchestration script → fixed
4. No-op security allowlist (line:0 never matched) → fixed with wildcard
5. Unlogged scope-shift in ASSUMPTIONS.md → fixed (self-violation of the new §8 rule)
6. Vacuous green (passed==0 accepted as PASS) → fixed
7. None==None sha bypass → fixed (require non-empty digests)
8. Missing-bundle crash → fixed (structured FAIL_CLOSED)

The §8 scope-shift rule was added to OPERATING-RULES.md: when scope shifts mid-phase, name it, decide whether to absorb or push out, and record the decision.

Final review: grok-4.5 ACCEPT-WITH-NITS, gemini-3.1-pro-preview ACCEPT. Merged to main.

**Key files created:** `phase-3.2/evidence/`, `tools/orchestrate-review.py`, `tools/OPERATING-RULES.md` §8, `planning/ROADMAP-REVIEW-PROMPT.md`, `telemetry/SCHEMA.md` v2

## Longest-standing features

- **`phase-1/scripts/verify-green.py`** — created Aug 5, still the locked-hash gate for every phase. Unchanged in its core logic: recompute sha256, compare to manifest, run pytest, refuse GREEN on mismatch.
- **`tools/adapters/factory.py`** — created Aug 5, the vendor shim that normalizes droid exec output. Designed from the start for multi-vendor extensibility (Claude, Codex, Ollama).
- **`tools/run-with-model.sh`** — created Aug 6, the enforcement wrapper that refuses to run droid exec without `--model` set. 1310 bytes, never needed to change.
- **The four invariants** (family separation, fresh review context, independent test authorship, valid RED before GREEN) — defined in the original PRD, unchanged through every phase.

## Major rewrites

- **§17.1 refinement (Aug 6-7):** The original "silent --auto is forbidden" was replaced with the attribution-vs-enforcement distinction. Auto is allowed at author seats (planner, executor) if the resolved model is recorded; it is forbidden at separation-bearing seats (validator, reviewer). This was a real policy change, not a clarification.
- **Telemetry SCHEMA v1 → v2 (Aug 8):** The role enum was extended with `test-designer` (KI-4 fix — the data already used it, the schema just didn't list it). Four new optional fields were added for the H-CI fairness rule: `evidence_source`, `mcp_call_tokens`, `mcp_payload_tokens`, `raw_test_output_tokens`.

## Growth trajectory

The codebase grew from a single PRD file to 285 source files across 8 phases in 5 days:

| Date | Phase | Files added | Key addition |
|---|---|---|---|
| Aug 3 | Conception | 1 | PRD.md |
| Aug 3-5 | Phase 0 + 0.5 | ~170 | Probes, fixtures, gates, adapter |
| Aug 5-6 | Phase 1 | ~20 | Lock/valid-red/verify-green scripts |
| Aug 6 | Conventions | ~10 | Model discipline, telemetry schema |
| Aug 6-7 | Phase 2 | ~18 | Planning brief, approval |
| Aug 7 | Phase 3 | ~41 | Execution prompts, evidence, telemetry |
| Aug 7 | Phase 3.1 | ~59 | Degraded loop results |
| Aug 7-8 | Phase 3.2 | ~28 | Evidence provider, orchestration, reviews |

The steepest growth was Aug 7, when Phase 3, 3.1, and the 3.2 spec all landed in the same day. The project went from "first execution" to "evidence externalization plan" in about 24 hours.

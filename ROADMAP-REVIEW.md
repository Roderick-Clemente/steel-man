# ROADMAP-REVIEW.md

**Date:** 2026-08-08 (v3 — reconciled with two rounds of cross-family panel review)
**Scope:** Full project arc (Phase 0 through Phase 3.2)
**Method:** Orchestrator hydration on all project docs + one explorer sub-agent per phase, synthesized into this review, then cross-family reviewed by Grok-4.5 + Gemini-3.1-pro-preview across two rounds. v1 was REJECTED by both reviewers for factual errors; v2 was APPROVE-WITH-NITS by both; this v3 folds in the v2 nits.
**Status:** Planning artifact for human review. No code was modified in the production of this document.

---

## Cross-family panel review history

| Version | Reviewers | Verdict | Key changes |
|---|---|---|---|
| v1 | Grok-4.5 + Gemini-3.1-pro | **REJECT** (both) | Phase 0.5 exists and closed; orchestration partially ran; signing key was fixed; telemetry has 12 rows not 6; §12 conflicts with PRD §13 |
| v2 | Grok-4.5 + Gemini-3.1-pro | **APPROVE-WITH-NITS** (both) | Directionally correct; nits: Evidence Provider IS the KI-2 fix; H3 not scheduled; parallelize tracks; Act 3 overclaims; §10 forward-looking only; stray-write STOP is dirty-tree false positive |
| v3 (this) | — | — | Folds in all v2 nits: parallel tracks, H3 scheduling, KI-2-as-bundle-fix, Act 3 bounded, §10 forward-looking, hermetic stray-write, run-with-model bypass |

Panel findings: `phase-3.2/reviews/roadmap-review-cross-family-findings.json` (v1), `phase-3.2/reviews/roadmap-review-v2-cross-family-findings.json` (v2)

---

## 1. What's Been Done

| Phase | Objective | Status | Key finding / lesson |
|---|---|---|---|
| **0** | Feasibility spike: 7+1 probes against Factory platform | **GO** (command-orchestrated) | "The platform cannot fail loudly" — 4 independent silent-green shapes. The reference guard (one PreToolUse hook) is the spine. Probes 5 & 7 remain unanswered (inferred from Probe 1's mission no-op). |
| **0.5** | Manual baseline harness (§13 comparison arm, Act 1 of demo) | **DONE** (`tools/PHASE-0.5-CLOSE.md`) | Headless real runs, blind validators, reality-asserting gates, cost/latency/intervention logging (operator-intervention = 1), fake-pass regression fixture. All exit criteria checked. Act 1 substance exists but has not been packaged as a demo beat. |
| **1** | Test-evidence vertical slice: lock, valid-RED, GREEN verify | **Partial** | Lock + GREEN verification works. `valid-red.py` was never run (RED read from test-designer's envelope). Invalid-RED rejection never demonstrated. `review-tests` skill never ported. Executor was handed the exact fix. Two items are cheap to close now (run valid-red.py + create invalid-RED fixtures); two are taken Ls (review-tests port, executor prompt). |
| **2** | Adversarial planning slice: blind review, reconciliation, oversight | **Complete (clean null)** | Plan reached hash-bound APPROVE. Round 1 converged with zero blocking/high — a valid outcome per PRD §13 ("a clean null result is valid data"). Reconciliation machinery (round cap, hash-rebinding, decision packets) was never triggered. Telemetry rows not written at the time but are reconstructable from 5 committed envelopes + `findings.md`. |
| **3** | End-to-end execution: 3 chunks through full loop | **Core done, exits missed** | 3 chunks built, all cross-family ACCEPT, 99 tests passing. No replayable demo, no baseline comparison, no local PR creation (3 of 4 exit criteria unmet). Orchestration was manual. Retry/re-plan path never exercised (0 rejections — clean null, valid per PRD §13). Phase 3 telemetry rows reconstructable from 13 committed envelopes via `gen-telemetry.py`. |
| **3.1** | Degraded loop spike: same-family test-author + executor | **Complete** | Same-family author encoded test-independence bias in 1 of 3 chunks. Panel split: grok caught it, gemini dismissed the identical failure. Deterministic standalone gate caught it every time. Cost 2.38x control (mostly from retry cycle). Fed back into PRD §17.6 — a good feedback loop. |
| **3.2** | Evidence provider: local EvidenceBundle, zero-CI | **Complete (milestone)** | All 4 scoped deliverables built and demoed. Orchestration script (`orchestrate-review.py`) ran with partial success — 12 telemetry rows in `runs.jsonl`, 10 from orchestrated runs with real decisions (ACCEPT, REJECT, ACCEPT-WITH-NITS, ERROR, UNKNOWN). Residual flakiness: ERROR/UNKNOWN rows on some gemini runs + non-hermetic stray-write check (dirty-tree false positive STOP). H-CI experiment designed but not run. Signing key vulnerability was found by grok and **already fixed** (`local_backend.py` now uses `os.urandom(32)`, consumer requires explicit key). Token saving (55.2%) is directional only and doesn't hold at locked-test-only scope. |

### Honest summary

The project has demonstrated the **mechanism** — the core invariants (family separation, test locking, valid-RED, cross-family validation) are real and work. Phase 0.5 (the manual baseline) is closed. The evidence provider is built and partially orchestrated. The telemetry system is incomplete but reconstructable from committed envelopes. The demo narrative's three acts are not yet packaged (Act 1 substance exists, Act 2 needs command-orchestrated framing not Mission-native, Act 3 is Phase-0-verified capabilities). The most important thing built is **knowledge about what the platform can and cannot do**, plus a working but flaky orchestration loop that needs stabilization, not invention.

---

## 2. What's Next (Current Roadmap As Written)

The current sequencing, inferred from the SPIKE documents, BUILD-NOTES follow-ons, and PRD §11:

1. **3.2 follow-on**: Harness backend (SPIKE §2.3 flavor b) — pull native tests/coverage/SARIF via Harness MCP
2. **H-CI experiment**: Full N-run A/B comparison (local vs in-session evidence, same models/prompts/diff, provider tokenizers)
3. **3.3 visual/behavioral tier**: Screenshot/DOM evidence lens (SPIKE seed exists)
4. **Framework-repo dogfood**: Run the framework's own deterministic assets through the same bundle contract (SPIKE §7)
5. **Phase 6 hardening**: Settling pass — calibration, regex tightening, ledger provenance, deferred findings
6. **Phase 7 human-in-the-loop compression**: Panel-based review with escalation knobs (post-MVP, pain-point-driven)

**Problem with the current order:** Harness backend before H-CI is backwards. H-CI is the economic fork — if the bundle doesn't save tokens, the Harness backend is infrastructure for a hypothesis that didn't hold. Both reviewers agreed: H-CI must precede Harness/3.3. **This review itself is Phase 4** (hardening + roadmap review), inserted ahead of the original schedule because the foundation needed attention before extending.

---

## 3. Missed Wins

### 3.1 Orchestration automation arrived late and is still flaky

A thin per-role invocation wrapper belonged at the Phase 0 contingency / Phase 1 spine (per `GO-NO-GO.md` build order). Full multi-validator review orchestration belonged no later than Phase 3 kickoff. Instead, `orchestrate-review.py` was built during Phase 3.2 and ran with **partial success** — 12 telemetry rows in `runs.jsonl`, 10 from orchestrated runs with real decisions (ACCEPT×6, ACCEPT-WITH-NITS×2, REJECT×2, ERROR×1, UNKNOWN×1).

**Actual residual flakiness** (corrected per v2 panel finding F-RR-v2-002): the primary live defects are ERROR/UNKNOWN verdict rows (gemini returning 0 tokens on some runs) and a non-hermetic stray-write check that STOPs on pre-existing dirty-tree paths (false positive, not validator mutation of product code). The 0-byte files observed in v1 were roadmap-review artifacts, not the orchestrated product path. The script already catches empty/malformed envelopes via `JSONDecodeError` — the missing feature is transient retry logic for provider API failures.

**What it cost:** Phases 1-3 ran reviews by hand. Phase 2 telemetry rows were never written. The orchestration script exists and partially works but needs stabilization (use adapter shim + `run-with-model.sh`, add stray-write baseline, add transient retry, make multi-run deterministic) — not invention from nothing.

### 3.2 Telemetry system-of-record is incomplete but recoverable

`telemetry/runs.jsonl` currently has 12 rows, all Phase 3.2 (schema v2). Phase 2 wrote zero rows at the time. Phase 3's rows were overwritten. `telemetry/findings.jsonl` and `dispositions.jsonl` do not exist.

**However, the data is reconstructable from committed artifacts:**
- Phase 2: 5 envelopes in `phase-2/build-evidence/` + structured findings in `findings.md` = 5 runs.jsonl rows + 6 findings.jsonl rows
- Phase 3: 13 envelopes in `phase-3/build-evidence/` + `gen-telemetry.py` (the auditable recipe) = 13 runs.jsonl rows
- Phase 3.1: envelopes in `phase-3.1/build-evidence/` + `gen-telemetry.py` = additional rows

**What it cost:** The §13 efficacy evaluation's system-of-record is incomplete, but the evidence inputs are partially recoverable. The gap is "missing SoR" not "missing evidence." Phase 6 calibration input (`first_seen_in_panel_position`) exists as prose in wiki entries and in `findings.md`, not yet in structured JSONL.

**Reconstruction plan:** Generate Phase 2 + Phase 3 rows from committed envelopes, merge with existing Phase 3.2 rows (not overwrite). This is mechanical extraction, not re-running anything.

### 3.3 The reconciliation loop's adversarial path was never triggered

Phase 2's round 1 converged with zero blocking/high findings. No revision, no re-review, no decision packet, no round cap. The non-convergence escalation path has zero empirical validation.

**However:** per PRD §13, "a clean null result is valid data" and "models disagree at least once" is NOT a success gate. The exit criterion (hash-bound approval OR escalated non-convergence) was satisfied. The gap is real but it is a **calibration backlog item**, not a phase-completion failure. Existing disagreement corpora (Phase 2 amendments path, Phase 3.1 panel split, Phase 3.2 orchestrated grok REJECT vs gemini ACCEPT) should be mined before manufacturing new ones.

### 3.4 Invalid-RED rejection was never demonstrated (cheap to close)

Phase 1's exit criterion requires "invalid RED cases are rejected." `valid-red.py` contains 14 rejection patterns but was never run against a real RED. No test fixtures were created.

**Closure plan:** Run `valid-red.py` against the existing locked test (closes the "never run" gap). Create 3-4 invalid-RED fixtures (syntax-error test, tautological test, missing-import test, service-unavailable test) and run each through the classifier. This is approximately 30 minutes of work and closes both the "never run" and "never demonstrated rejection" gaps.

### 3.5 The `review-tests` skill was never ported (take the L)

PRD §11 Phase 1's first deliverable: "Port the existing `review-tests` skill." It was not done. The skill exists in QuantumBank's `.claude/skills/` but was never adapted into the framework.

**Disposition:** Take the L. Mark as a known gap. Schedule as a follow-on. Don't try to retrofit it now — it's a real deliverable that was skipped, not a quick fix.

### 3.6 Phase 3's exit criteria were partially unmet

Three of four PRD §11 Phase 3 exit criteria were not met:
- **Replayable demo**: No demo script or replay artifact exists.
- **Baseline comparison**: No comparison arm within Phase 3 (Phase 0.5 closed separately; 3.2 produced directional data only).
- **Local PR creation**: No PR was created — not even a draft.

The fourth (one complete run) was met: 3 chunks, 99 tests, all ACCEPT.

### 3.7 The executor was given the answer (take the L)

Phase 1's executor prompt specified the exact one-line fix. The executor's 4-turn, 1077-token run was mechanical, not independent implementation. H3 (cheap executors can do the work) was never genuinely tested.

**Disposition:** Take the L. This is a process lesson (proposed rule §13). The next executor prompt describes the problem, not the fix. Can't un-give the answer retroactively.

### 3.8 ~~The default signing key is forgeable~~ (CLOSED — fixed)

The grok reviewer found the default HMAC key was in-repo and forgeable. **This was already fixed:** `local_backend.py` now uses `os.urandom(32)` when `EVIDENCE_SIGNING_KEY` is unset, and the consumer requires an explicit key via `--signing-key-env`. No hardcoded secret remains in `*.py`.

**Residual gap:** Key distribution for multi-agent/CI use is still unspecified. This is a follow-on for when the evidence provider moves beyond local mode, not a current open trust hole.

### 3.9 Gemini is systematically non-blocking, not a no-op

Across Phase 2 and Phase 3, Gemini raised zero findings in every review. But Phase 3 envelopes show long, evidenced ACCEPTs — Gemini reads the repo and produces reasoning, it just doesn't block. The Phase 3.2 orchestrated runs strengthen this: gemini ACCEPT paired with grok REJECT on the same code.

**Disposition:** Phase 6 calibration input. Gemini is not a no-op reviewer (it produces long evidenced ACCEPTs) but it is systematically non-blocking relative to Grok. This is a precision/recall measurement question, not a roadmap fork by itself.

### 3.10 The orchestration script bypasses both the adapter shim and run-with-model.sh

`orchestrate-review.py` cites `tools/adapters/factory.py` and `tools/run-with-model.sh` in its docstring but reads raw Factory envelope fields directly in the implementation body and invokes `DROID_BIN` directly instead of routing through the model-discipline wrapper. This is a dual missed reuse: the adapter shim prevents vendor field-name drift (Phase 0 proved this is real), and `run-with-model.sh` enforces model-pinning discipline. Additionally, the stray-write check (`step3_check_stray_writes`) has no pre-run baseline — it STOPs on any dirty path, including pre-existing untracked files, producing false positives that break N-run H-CI.

### 3.11 Phase 0.5 is not packaged as Act 1 of the demo (panel finding)

`tools/PHASE-0.5-CLOSE.md` marks Phase 0.5 DONE with all exit criteria checked — headless runs, blind validators, reality-asserting gates, cost/latency/intervention logging. The Act 1 substance exists. What's missing is packaging it as the demo's Act 1 narrative beat and connecting it to a command-orchestrated Act 2.

### 3.12 Demo Act 2 is still Mission-native after the GO decision forbade that spine (panel finding)

PRD §15 Act 2 is written as Mission automation ("same sprint as a Mission"). But the Phase 0 GO-NO-GO decision was **command-orchestrated, not Mission-native** — Mission mode is a no-op at 0.186.0. The demo narrative has never been reconciled with this decision. Act 2 needs an honest rewrite around the command-orchestrated wrapper: "push a scripted button," not "kick off a Mission."

### 3.13 KI-2 validator Execute write vector — the Evidence Provider IS the preventive fix (panel v2 finding)

Across Phase 2 and Phase 3, `--auto high` + `Execute` is a write vector for validators. The current mitigation is a post-run `git status` check (detective, not preventive).

**However:** Phase 3.2's Evidence Provider is the preventive fix. In bundle-consuming mode, validators read the EvidenceBundle instead of running pytest — so `Execute` can be removed from their `--enabled-tools` entirely, fully closing the write vector. The SPIKE itself noted this: "a read-only evidence pull is strictly safer than the current in-session `Execute`-at-`--auto-high` pytest run" (§5).

**Constraint:** The KI-2 fix (removing `Execute` from validators) must be **parameterized** based on evidence source. The H-CI control arm (`evidence_source=in-session`) still requires `Execute` for in-session pytest. Only the treatment arm (`evidence_source=bundle`) can safely drop it. Applying the fix universally would break the H-CI control arm (v2 panel finding F-RR-018).

### 3.14 "Close the laptop" durability was never evidenced (panel finding)

The demo narrative's Act 2 promise is "close the laptop and come back to a completed sprint." No evidence exists that the command-orchestrated loop can survive a laptop close (no durable runner, no checkpoint-and-resume beyond rate-limit backoff). This is a demo blocker: don't claim autonomy that hasn't been demonstrated.

---

## 4. Roadmap Proposal

### Capacity envelope

Before proposing a sequence, name the constraints that shape it (panel finding F-RR-014):

- **Platform:** Mission-native path is closed (GO-NO-GO). No "close the laptop" durability has been evidenced. Silent-green is structural.
- **Seats:** OpenAI executor tier was unavailable (KI-1). Model availability is not guaranteed.
- **Near-term capacity:** This is not an unbounded program. The next deliverables should be 1-3 bounded items, not a five-priority expansion. Refuse unbounded foundation programs.

### Proposed re-sequencing (v3 — Phase 4 parallel tracks, adopted from both panel rounds)

The v2 serial priority list (P0-P5) was improved by both reviewers: Grok proposed three parallelizable tracks instead of six serial buckets (F-RR-v2-003); Gemini noted H3 was never scheduled (F-RR-017) and that the Evidence Provider is the KI-2 fix (F-RR-015). This v3 adopts both. These tracks constitute **Phase 4 (Hardening + roadmap review)** in the updated PRD §11 delivery plan.

**Track A — Cheap closures + Act 1 packaging (parallel, non-gating)**

1. **Run `valid-red.py`** against the existing locked test (closes the "never run" gap).
2. **Create 3-4 invalid-RED fixtures** and run each through the classifier (closes the "invalid RED never demonstrated" gap).
3. **Package Act 1** from `tools/PHASE-0.5-CLOSE.md` — the substance exists, just needs demo-narrative packaging.
4. **Reconstruct Phase 2 + Phase 3 telemetry rows** from committed envelopes, merge with existing Phase 3.2 rows. Non-gating hygiene for the §13 system of record.

These are not new features. They are mechanical extraction and packaging of artifacts that already exist.

**Track B — Orchestration harden → H-CI → H3 (serial economic fork)**

1. **Harden orchestration just enough** for N identical runs (days, not a program):
   - Use `tools/adapters/factory.py` + `tools/run-with-model.sh` instead of raw parsing / direct `DROID_BIN` (§14).
   - Add stray-write baseline so dirty-tree paths don't false-positive STOP.
   - Add transient retry logic for provider API failures (the actual cause of ERROR/UNKNOWN rows, not empty envelopes).
   - Make multi-run deterministic.
   - Keep the telemetry append path that already works.
   - **Bound this to the minimum needed for credible N-run A/B.** Do not gate H-CI on demo packaging or full KI-2 redesign.

2. **Run the H-CI experiment** (review-side cost fork): same locked chunk, same models/prompts/diff, only the evidence source changes. Use provider tokenizers. Parameterize the KI-2 fix: treatment arm (bundle) drops `Execute` from validators; control arm (in-session) keeps it. This determines whether the evidence-provider abstraction saves tokens on the review side.

3. **Run an H3 validation** (execution-side cost fork): one genuine, un-hinted executor chunk — the prompt describes the problem, not the fix. This tests whether cheap executors can actually implement, which is the primary cost-saving mechanism of the sprint method. H-CI measures review-side savings; H3 measures execution-side capability. Both are needed for the full cost thesis.

**Why serial within Track B:** H-CI needs a stable-enough orchestrator. H3 needs the same loop. But neither needs demo packaging or telemetry reconstruction to proceed.

**Track C — Demo honesty (overlaps Track B after harden)**

1. **Rewrite Act 2** as command-orchestrated, not Mission-native. "Push a scripted button" is the honest version. No Mission cosplay.
2. **Preventive KI-2** in the demo: in bundle-consuming mode, validators don't get `Execute`. This is the Evidence Provider fix (§3.13), demonstrated live.
3. **Act 3 = Phase-0-verified controls ONLY.** Verified by Phase 0 probes: model pinning (Probe 2), hook enforcement (Probe 4), isolation guard (Probe 3), plugin scaffold (Probe 6). Droid Shield, OpenTelemetry export, and air-gapped deployment were NOT verified — list as roadmap narrative only until re-probed (v2 panel finding F-RR-v2-004).
4. **"Close the laptop"** requires a demonstrated durable runner. Either build one or drop the claim. Do not demo autonomy that hasn't been evidenced.

**Why overlaps Track B:** Act 2 needs the hardened orchestrator from Track B step 1. Act 1 (Track A) and Act 3 do not — they can proceed independently.

**Backlog D — Calibration + MVP acceptance (not gates for B or C)**

- Mine existing disagreement corpora: Phase 2 amendments, Phase 3.1 panel split, Phase 3.2 orchestrated REJECT/ACCEPT.
- **One controlled rejection drill** for PRD §12 v1 acceptance (replay an existing REJECT corpus through the retry state machine — calibration/acceptance, not phase reopen).
- Gemini precision/recall study (Phase 6 calibration input).
- `review-tests` skill port remains a taken L / scheduled follow-on.

**Backlog E — Evidence-tier extension (only after H-CI)**

Harness backend, 3.3 visual tier, framework-repo dogfood. Only after H-CI returns a non-null result. **Note:** even a null H-CI (no token savings) may still justify a thin flavor-(a) CI-as-runner for security/trust-boundary benefits — the fork is not *purely* economic (v2 panel finding F-RR-019). But flavor-(b) Harness-native investment as a cost play requires a non-null result.

**Deferred (unchanged):** Phase 6 hardening settling pass; Phase 7 human compression post-MVP pain.

### Deadlock check

- H-CI needs a stable-enough orchestrator (Track B step 1 before step 2). ✓
- H3 needs the same loop (Track B step 1 before step 3). ✓
- Demo Act 1 does NOT need Track B (0.5 already closed). Can start in Track A. ✓
- Demo Act 2 needs Track B step 1 (working orchestration). ✓
- Demo does NOT need H-CI or H3 results (mechanism demo is viable regardless). ✓
- KI-2 fix is parameterized: treatment arm drops `Execute`, control arm keeps it. No deadlock with H-CI. ✓
- Calibration backlog does not block H-CI or demo. ✓
- No later track is a hidden prerequisite for an earlier one. ✓

### Demo strategy decision (panel finding F-RR-007)

The PRD §15 Act 2 is Mission-shaped ("same sprint as a Mission"). The GO-NO-GO decision was command-orchestrated. This tension must be resolved explicitly:

**Decision: rewrite Act 2 around the command-orchestrated wrapper.** "Push a scripted button" is the honest version. "Close the laptop" requires a durable runner that has not been evidenced — either build one or drop the claim. No Mission cosplay.

---

## 5. Process Improvements

### Rules to add to `tools/OPERATING-RULES.md`

**§9 — If it's not scripted, it didn't happen (or: "RUN-COMMANDS.md is not a script")**

A phase that runs its `droid exec` invocations by manually copy-pasting commands has no reproducible evidence. The orchestration script must be the default way reviews are run. A RUN-COMMANDS.md file is documentation for the script, not a substitute for it. If the script doesn't exist yet, the first deliverable of the phase is to build it — **bounded to the phase's actual repeat surface**, not a full panel orchestrator by default (v2 panel finding F-RR-v2-006).

*Exception:* pure probe spikes (Phase 0-style) may run manually — they are one-off capability checks, not repeatable loops.

*Rationale:* Phases 1-3 ran manually. The orchestration script was built in 3.2 and partially works. This rule makes "script the loop" the default, not the retrofit.

**§10 — Telemetry rows are written by the script, not by the operator (forward-looking)**

From adoption forward, multi-invocation phases must emit `runs.jsonl` (and `findings.jsonl` / `dispositions.jsonl` when applicable) from the orchestration script as part of each `droid exec` invocation, not appended manually after the fact. Committed envelopes + auditable reconstruction recipes (e.g. `gen-telemetry.py`) remain valid evidence for past phases and disaster recovery. Do not equate "missing live SoR row" with "phase incomplete" when reconstructable artifacts exist (v2 panel finding F-RR-v2-005).

*Rationale:* Phase 2 planned telemetry in detail and wrote zero rows. Phase 3's rows were overwritten. Phase 0.5 and Phase 1 used `RUN-LEDGER.md` as their SoR, which was valid at the time. This rule is forward-looking, not retroactive.

**§11 — Exit criteria are checked, not assumed**

A phase's exit criteria must be checked against actual artifacts before the phase is declared complete. "Invalid RED cases are rejected" means at least one invalid-RED case was run and rejected — not that the classifier script exists. "Replayable demo" means a demo artifact exists — not that the wiki entry is comprehensive. "Local PR creation" means a PR was created — not that the README says "present the slice."

*Rationale:* Phase 1 declared "invalid RED cases are rejected" as met, but `valid-red.py` was never run. Phase 3 declared completion without a demo, baseline comparison, or PR. The exit criteria exist to be checked, not to be interpreted.

**§12 — Unexercised safety paths are named gaps, not phase blockers**

If a phase's purpose is to test a mechanism (reconciliation, validation blocking, retry/re-plan), and the mechanism was not triggered (e.g., the plan converged on round 1, or all validators returned ACCEPT), the phase is **complete with a clean null result** — this is valid data per PRD §13 ("a clean null result is valid data; models disagree at least once is NOT a success gate"). The unexercised path must be **recorded as a named gap/follow-on** in the phase's KNOWN-ISSUES.md. Optional adversarial fixtures may be built as calibration work, but they are **not exit gates**.

*Rationale:* Phase 2's reconciliation loop was never tested under disagreement. Phase 3's retry path was never exercised. Both are valid completions with named gaps. Forcing disagreement would incentivize manufactured findings — the exact failure mode PRD §13 warns against. (This rule replaces the v1 §12 which incorrectly treated clean nulls as incomplete. Corrected per cross-family panel finding F-RR-005.)

**§13 — Don't give the executor the answer**

The executor prompt must describe the problem and the constraints, not the implementation. If the prompt contains the exact code change to make, the executor is a `sed` command, not an independent implementation. The cheap-executor seat's value (H3) depends on the executor solving the problem, not applying a known fix.

*Rationale:* Phase 1's executor prompt specified the exact one-line fix. The executor's 4-turn run confirmed it was mechanical. The H3 cost hypothesis (cheap executors can do the work) was never genuinely tested.

**§14 — Use the adapter shim and the model-discipline wrapper**

Any script that reads `droid exec` envelope data must go through `tools/adapters/factory.py` (or the equivalent vendor adapter). Any script that invokes `droid exec` must go through `tools/run-with-model.sh` (or the equivalent model-discipline wrapper). Reading raw envelope fields directly or invoking `DROID_BIN` directly bypasses both the vendor-neutral abstraction and the model-pinning enforcement, making the code brittle to platform field-name drift and model-discipline gaps (v2 panel finding F-RR-v2-008).

*Rationale:* `orchestrate-review.py` cites both the adapter and `run-with-model.sh` in its docstring but bypasses both in the implementation body. When a docstring cites a shim/wrapper, the implementation must call it — or the citation is a §8-style silent scope lie.

**§15 — Assert on reality includes git history (panel finding, proposed by Gemini)**

Never judge the success of past phases solely on uncommitted working tree state. Always inspect git history and the system of record (committed artifacts, telemetry, lock manifests) before concluding that something was "never built" or "never ran." A dirty working directory with empty files is not evidence of failure if the committed state and telemetry tell a different story.

*Rationale:* The v1 of this review concluded that `orchestrate-review.py` "never successfully ran" based on 0-byte files in a dirty working tree. The committed telemetry (12 rows, 8 from orchestrated runs with real decisions) told a different story. This is the exact failure mode §7 warns about, extended to include git history as part of "reality."

**§16 — Demo claims bind to Phase-0-verified capabilities and the command-orchestrated GO decision (panel finding F-RR-012)**

No demo beat may claim a capability that Phase 0 did not verify. Act 2 must be honest about the command-orchestrated spine — no Mission cosplay. "Close the laptop" requires a demonstrated durable runner, not a promise. Act 3 stays inside the probes that returned PASS.

*Rationale:* The PRD §15 Act 2 is Mission-shaped, but the GO-NO-GO decision was command-orchestrated. The demo narrative has never been reconciled with this decision. An audience will catch a Mission demo that doesn't actually use Missions.

**§17 — Capacity envelope: name the next 1-3 deliverables; refuse unbounded foundation programs (panel finding F-RR-014)**

A roadmap re-sequencing must name a capacity bound: what can actually be done next, not an unbounded list of priorities. If the proposed work is a "foundation program" with no clear exit, it is the same anti-pattern as the missed exits it criticizes.

*Rationale:* The v1 of this review proposed five priorities and six rules without naming constraints. The cross-family panel flagged this as recreating the unbounded-backlog pattern.

### Existing rules that were violated but should be enforced

- **§7 (Assert on reality, never on exit code):** Phase 1's RED verification asserted on the test-designer's natural-language envelope, not on `valid-red.py`'s exit code. The v1 of this review asserted on a dirty working tree instead of checking git history. Both are the same failure: trusting a plausible-looking signal over the actual artifacts.
- **§8 (When scope shifts, name it):** Phase 0's Probe 8 was added without an ASSUMPTIONS.md entry. Phase 3.2's orchestration script was built without being named as a scope shift (the rule was written retroactively). Phase 3.1/3.2/3.3 were spawned as new sub-phases without being named as deviations from the Phase 3 plan. The rule exists; it was not applied in real-time.
- **§5 (No unsupervised building — the gate is the point):** Phase 3's exit criteria were partially unmet (no demo, no baseline, no PR), but the phase was effectively treated as complete. The gate was not enforced.

---

## Appendix A: Sub-Agent Audit Summary (v1)

| Phase | Sub-agent | Key gaps surfaced |
|---|---|---|
| 0 | Explorer | Probes 5/7 unanswered; Droids not paired; no run-all script; Probe 8 scope shift unnamed |
| 1 | Explorer | `review-tests` not ported; `valid-red.py` never run; invalid-RED never tested; KNOWN-ISSUES empty; executor given the answer |
| 2 | Explorer | Reconciliation never exercised; zero telemetry rows; no findings.jsonl; collision guard untested; KI-2 write vector unresolved; Gemini 0 findings |
| 3 | Explorer | No demo/baseline/PR; telemetry rows lost; retry path untested; reviews dir empty; orchestration manual; 3 sub-phases spawned unnamed |
| 3.1 | (from hydration) | Follow-up experiments proposed but unsequenced; worktree isolation manual; §17.6 feedback loop is good |
| 3.2 | Explorer | Orchestration script built but not validated; H-CI not run; signing key forgeable; allowlist stub; coverage non-functional; script bypasses adapter |

*Note: Several v1 findings were corrected by the cross-family panel. See Appendix B.*

---

## Appendix B: Cross-Family Panel Reconciliation (v1 → v2)

| Panel finding | v1 claim | Correction | v2 status |
|---|---|---|---|
| F-RR-001 (blocker) | "Act 1 was never built" | Phase 0.5 closed (`tools/PHASE-0.5-CLOSE.md`), all exit criteria checked | **Corrected** — §1 table, §3.11, §4 P3 |
| F-RR-002 (high) | "Orchestration never successfully ran" | 12 telemetry rows, 8 from orchestrated runs with real decisions; partial success with flakiness | **Corrected** — §1 table, §3.1, §4 P1 |
| F-RR-003 (medium) | "runs.jsonl has 6 rows; no §13 data" | 12 rows; §13 inputs partially recoverable from committed envelopes | **Corrected** — §3.2 |
| F-RR-004 (medium) | "Default signing key is forgeable" | Already fixed: `os.urandom(32)`, consumer requires explicit key | **Closed** — §3.8 |
| F-RR-005 (high) | "§12: phases incomplete until safety paths fire" | Conflicts with PRD §13 null-result rule | **Rewritten** — §5 §12 |
| F-RR-006 (high) | "Fix orchestration first, then H-CI, then adversarial, then demo" | Orchestration needs stabilization not invention; H-CI is the economic fork; demo can start now (0.5 exists) | **Adopted** — §4 re-sequencing |
| F-RR-007 (high) | "Demo treatment adequate" | Act 2 still Mission-native after GO forbade it; needs honest rewrite | **Adopted** — §4 demo strategy, §5 §16 |
| F-RR-008 (medium) | "Should have been built in Phase 1" | Phase 1 exit is thinner; full orchestration belonged at Phase 3 | **Corrected** — §3.1 |
| F-RR-009 (medium) | "Deliberately construct blocking cases" | Mine existing disagreement first; calibration not gates | **Adopted** — §3.3, §4 P4 |
| F-RR-010 (low) | "Gemini is a rubber-stamp" | Gemini is non-blocking, not a no-op; produces long evidenced ACCEPTs | **Corrected** — §3.9 |
| F-RR-011 (medium) | "Listed missed wins are the material set" | Missing: 0.5 not packaged, Act 2 not rewritten, KI-2 write vector, no laptop-closed durability | **Added** — §3.11-3.14 |
| F-RR-012 (medium) | "Rules §9-§14 are sound" | Accept §9-§11, §13-§14; reject §12; add demo-claim binding + capacity envelope rules | **Adopted** — §5 §15-§17 |
| F-RR-013 (low) | "Harness before H-CI is wrong" | Agree; keep deferral | **Unchanged** — §4 P5 |
| F-RR-014 (medium) | "No capacity envelope" | Add constraints stanza; refuse unbounded foundation programs | **Adopted** — §4 capacity envelope, §5 §17 |
| Gemini F-RR-005 | (Meta-finding) | v1 asserted on dirty working tree, not git history; proposed new operating rule | **Adopted** — §5 §15 |

---

## Appendix C: v2 Panel Nit Reconciliation (v2 → v3)

| v2 panel finding | v2 claim | Correction | v3 status |
|---|---|---|---|
| F-RR-v2-001 (medium) | "8 orchestrated rows" | 10 orchestrated + 2 prior review = 12 total | **Corrected** — §1 table, §3.1 |
| F-RR-v2-002 (medium) | "Empty envelopes are the residual" | 0-byte files are roadmap-review artifacts; real residual is ERROR/UNKNOWN + non-hermetic stray-write STOP | **Corrected** — §3.1, Track B step 1 |
| F-RR-v2-003 (high) | "Six serial priorities" | Three parallelizable tracks, not six buckets | **Adopted** — §4 Track A/B/C/D/E |
| F-RR-v2-004 (medium) | "Act 3 lists Droid Shield/OTel as verified" | Phase 0 did not verify Shield/OTel; list as roadmap narrative only | **Adopted** — Track C step 3 |
| F-RR-v2-005 (medium) | "§10 retroactively voids past completions" | Forward-looking only; RUN-LEDGER.md was valid SoR for 0.5/1 | **Adopted** — §5 §10 rewritten |
| F-RR-v2-006 (low) | "§9 re-expands into foundation program" | Bound to phase's actual repeat surface | **Adopted** — §5 §9 tightened |
| F-RR-v2-007 (low) | "Bound P1 to minimum for H-CI" | Do not gate H-CI on demo or full KI-2 redesign | **Adopted** — Track B step 1 |
| F-RR-v2-008 (low) | "Also bypasses run-with-model.sh" | Dual shim bypass + non-hermetic stray-write | **Adopted** — §3.10, §5 §14 |
| F-RR-v2-009 (low) | "Add MVP controlled drill" | One controlled rejection drill for PRD §12 in calibration backlog | **Adopted** — Backlog D |
| F-RR-v2-010 (low) | "Null H-CI may still justify thin CI" | Fork is not purely economic | **Adopted** — Backlog E note |
| Gemini F-RR-015 (high) | "KI-2 not linked to Evidence Provider" | Evidence Provider IS the preventive fix in bundle mode | **Adopted** — §3.13, Track C step 2 |
| Gemini F-RR-016 (medium) | "Script already catches empty envelopes" | Missing feature is transient retry, not empty-envelope handling | **Adopted** — §3.1, Track B step 1 |
| Gemini F-RR-017 (high) | "H3 not scheduled" | Add H3 validation: genuine un-hinted executor test | **Adopted** — Track B step 3 |
| Gemini F-RR-018 (medium) | "Universal KI-2 fix breaks H-CI control arm" | Parameterize: treatment drops Execute, control keeps it | **Adopted** — §3.13, Track B step 2 |
| Gemini F-RR-019 (medium) | "H-CI null ≠ Harness worthless" | Security/trust benefits exist independent of token savings | **Adopted** — Backlog E note |

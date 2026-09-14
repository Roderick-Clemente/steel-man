# PR Bodies — review-cleanup stack

Base-chained: PR 1 → main, PR 2 → PR 1, PR 3 → PR 2, … PR 7 → PR 6.
Retire `factory/schema-v3-and-subagent-executor` once the stack opens.
Audit trail: `planning/review-cleanup/` (prompts, reports, punch lists).

---

## PR 1 — Telemetry schema v3 (`factory/v3-telemetry-schema` → `main`)

**Declares telemetry schema v3 and makes the docs match the emitters.**

Schema v3 adds per-seat outcome rows, run provenance (git branch, commit, model), and an all-seat telemetry surface so every invocation — not just the executor — is countable in the aggregate. This PR also fixes review findings in the telemetry layer: front matter updated v2→v3, the `overridden` disposition documented, validator rows stamped with the real `git branch` instead of a hardcoded literal, `phase_step` and `reached_phase_step` enums aligned with what the runner actually emits (the never-emitted `validate` removed), and a dead `"result" in locals()` guard cleaned up.

Each fix carries a doc-pinning or behavioral regression test. v1/v2 rows are unchanged — the aggregator's backward compatibility is preserved.

**KIs closed:** none directly (schema declaration). **Findings fixed:** 5 (front matter, dispositions enum, validator branch, enum alignment, dead guard).

---

## PR 2 — Planner integrity (`factory/planner-integrity` → `factory/v3-telemetry-schema`)

**Makes the planner seat's inputs and outputs trustworthy.**

Four fixes that harden the planning layer:
- **KI-7:** the plan is the seat's final message, validated structurally — a chat summary that describes a plan without being one is refused.
- **KI-8:** the planner works against the operator's authored chunk contract, not a guess derived from the spec.
- The plan-review loop now truly iterates, and its evidence is round-indexed (`plan-r{N}.md`, `plan-prompt-r{N}.md`) so no round overwrites the text a verdict hash-binds to.
- Checkpoint save/load becomes field-driven for both `RunState` and `ChunkState` — future dataclass fields round-trip by construction instead of requiring a matching hand-restored line. A programmatic sentinel sweep test iterates every field and fails loudly if restore drops one.
- The `ACCEPTED_ASSERTION` parse the test-designer prompt always promised but no code implemented is now wired: `parse_accepted_assertion` extracts the designer's phrase (last-match discipline) and threads it into `lock_test`/`validate_red`.

**KIs closed:** KI-7, KI-8. **Note:** the KI-7 tool-policy claim (planner has no file-writing tool) is completed at the stack top — PR 7's `77c6ae6` makes the live entrypoint derive seat allowlists from `DEFAULT_ENABLED_TOOLS`, so the planner's `Read,Glob,Grep,LS` (no `Execute`) reaches `droid exec` on the default path.

---

## PR 3 — RED structural classification (`factory/red-structural-classification` → `factory/planner-integrity`)

**The RED gate classifies on pytest's structural evidence, not substring matching.**

KI-9 replaced the old substring classifier with one that reads pytest's structural signals (collected count, ERRORS vs FAILURES sections, exit code) — so a test that explains its own RED is no longer punished for mentioning "conftest" in its assertion message. This PR also fixes:

- **KI-17:** pytest's `warnings summary` section names source files (e.g. `conftest.py:5`) and sits outside the FAILURES region — the old fallback matched collection-phase signatures against that region and rejected valid REDs for any pilot whose conftest emits a deprecation warning. The warnings-summary section is now excluded from the fallback scan. (KI-17 was renumbered from KI-14 to avoid a collision with PR 4's cherry-picked entry; the renumbering is documented in-file.)
- Dead `INVALID_RED_SIGNATURES` aggregate removed (no production callers).
- The evidence producer's timeout is now a shared budget (`evidence_timeout.py`) that sums every enabled inner step plus grace, and `orchestrate-review.py` catches `TimeoutExpired` and fails closed with a diagnosable message instead of a bare traceback.

**KIs closed:** KI-9, KI-17. **Findings fixed:** 4 (warnings exclusion, dead code, timeout budget, KI-17 renumber).

---

## PR 4 — Rejection routing and feedback (`factory/rejection-routing-and-feedback` → `factory/red-structural-classification`)

**Rejections route to the seat that can act on them, carrying the rejecting validator's own finding.**

The flagship PR. Five fixes that complete the adversarial seat routing:

- **KI-16:** a `REJECT_IMPLEMENTATION` retry now reaches the executor with the validator's finding rendered into its prompt. Previously the retry re-entered `run_chunk_inner`, hit `validate_red` ("Invalid RED: test passed" — the rejected implementation is GREEN at HEAD), and burned retries at the RED gate until `HUMAN_DECISION`. The relaxation now covers the implementation-retry round (GREEN is the expected starting state), confirmed before proceeding. Pinned by an end-to-end test that drives the real lock/RED/GREEN/evidence gates with only droid seats stubbed.
- **KI-19:** `VERDICT: REPLAN` was offered in the validator prompt but the parser had no token for it — a validator following the prompt got parsed as a stray prose word. Removed from the prompt (the chunk lifecycle had no safe transition back to planning); reimplemented for real in PR 7.
- **Vocab extraction:** `sprint_loop/vocab.py` is the single source for verdict strings, executor result signals, and phase-step values. Contract tests bind the validator prompt's verdict block, the orchestrate-review parser, and the routing set to the shared constants — drift is now a test failure, not a runtime surprise. The `tagged_line_pattern` builder also fixes a latent prefix-matching hazard (`ACCEPT` shadowing `ACCEPT-WITH-NITS`).
- **SPEC_OR_TEST_BLOCKED:** parsed from the last `RESULT:` line only (narrating the string no longer hard-blocks a GREEN chunk); executor.md now instructs the full `RESULT: SPEC_OR_TEST_BLOCKED` literal. Distinct exit code 6.
- **All-skipped regression:** an exit-0 suite with zero passed and only skipped tests is now refused as green evidence — the exact vacuous-green the gate already failed closed on for locked tests. The refusal logic is extracted into one shared module (`sprint_loop/regression.py`) and enforced at producer, consumer, and orchestrator gates.

**KIs closed:** KI-16, KI-19 (removed), KI-15 (cherry-picked). **Findings fixed:** 7.

---

## PR 5 — Executor experiment docs (`factory/executor-experiment-docs` → `factory/rejection-routing-and-feedback`)

**Documents the two-arm executor experiment and reframes its claims to what n=1 supports.**

The experiment compared kimi-k3 (cheap) vs gpt-5.2 (expensive) as executor seats on the same chunk. The rewrite keeps all raw data tables untouched and changes only the interpretation:

- The 4.4× executor-only credit gap (371,917 vs 85,394) is the clean signal and leads the summary — labeled explicitly as n=1 per arm.
- The full-pipeline headline is caveated: ~209K of the gap is a confounded manual re-run of the gemini validator (Arm A), which narrows the ~30% pipeline gap to ~15% when that seat is excluded.
- KI-18 broke the controlled variable (Arm B ran a 20-test suite after a test-designer bounce vs Arm A's original 7), which contaminates the lines-produced and code-quality comparisons — asterisked in every section that cites them.
- The transferable finding leads the conclusion: credits = price-per-token × volume, and volume dominated (32,747 vs 6,339 output tokens; 20 vs 13 turns) — the "cheap executor" hypothesis was ill-posed, not merely false.
- "Code quality parity" is softened to "no defect found by either validator; independent review pending."
- The run ledger is reconciled through KI-19; KI-18 is filed.

**Stance:** the data leans toward gpt-5.2 having lower total cost of ownership, but this is still being tested. A rerun plan (≥3 runs per arm, KI-18 fixed) is stated. (The reviewer-variance range is corrected to ~38–94% at the stack top, PR 7.)

**KIs filed:** KI-18.

---

## PR 6 — Runner hygiene (`factory/runner-hygiene` → `factory/executor-experiment-docs`)

**Cleanup with no behavior change. Net -103 lines.**

Five scoped items, one commit each:
1. Dead shadowed first `main()` removed (was kept only to satisfy `noqa: F811`); help rendering already owned by the surviving entrypoint.
2. Force-accept disposition block extracted into one `_apply_force_accept_disposition` helper — the two verbatim copies had already diverged on checkpoint writing.
3. Shared `tests/conftest.py` consolidates the runner-loader, run-state, and stub-loop helpers that three test files pasted near-identically (and had already drifted: one tracked `td_phase_steps`, the others didn't).
4. Seat tool lists in executor.md and test-designer.md now render from `DEFAULT_ENABLED_TOOLS` via `{{enabled_tools}}` instead of hand-written names (the old names included `Write`/`MultiEdit`, ids the CLI doesn't register).
5. Planner.md's `PLAN_HASH` footer aligned with actual behavior (the runner hashes the message verbatim; no substitution occurs).

**KIs closed:** none. **Findings fixed:** 5 hygiene items.

---

## PR 7 — Plan-defect route + final review punch list (`factory/plan-defect-route` → `factory/runner-hygiene`)

**Implements the plan-defect escape route and carries the final review punch list.**

Two features plus four review fixes:

**REPLAN done right (KI-19 fast follow):** `VERDICT: REPLAN` is reintroduced as a first-class verdict through `vocab.py` end to end — prompt block, gate parser, and routing all driven from the shared constants. On a REPLAN verdict, the chunk stops fail-closed (no executor/test-designer re-fire), the rejecting evidence is archived (`superseded-replan-round{N}`), the validator's finding is threaded into the next planner prompt, and the chunk list is re-derived from the chunks file — nothing from the rejected plan is reused. Bounded by `--replan-budget` (default 1); exhaustion escalates to `HUMAN_DECISION` with exit code 7. The budget and finding survive checkpoint resume.

**KI-18 pinned:** traced to the stack's REJECT_TEST routing (`lock_test` runs unconditionally on every `run_chunk_inner` entry), so the manifest is regenerated from the redesigned test before the next validation reads `locked_test_sha`. Pinned by `test_lock_relock_on_redesign.py`, which drives the real `lock.py` through the Arm B sequence (7-test → REJECT_TEST → 20-test → assert manifest SHA matches) plus the resume-mid-bounce variant.

**Final review punch list:**
- **N-1 [P1]:** `_main_inner::_make_role` now derives seat tool allowlists from `DEFAULT_ENABLED_TOOLS[role]` — the hardcoded literals that bypassed the dict (and kept `Execute` on the live planner path despite PR 2's fix) are deleted. The dict itself is corrected against the installed CLI's verified tool registry (no `ApplyPatch`/`MultiEdit`/`Write`). Test drives `main()` end-to-end in dry-run and asserts on the real RunState.
- **N-2 [P2]:** KI-20 filed — the REPLAN route is validated on single-chunk runs; multi-chunk replan passes re-run accepted chunks and fail their RED gate (design gap, OPEN, three fix directions documented).
- **N-4 [P2]:** RUN-LEDGER scorecard reconciled (20 found, 14 fixed, 3 open).
- **N-5 [P3]:** Experiment doc variance range corrected to ~38–94%.
- **N-8 [P3]:** Ledger KI-7 shape denominator corrected to twenty.

**Validation envelope stated honestly:** the REPLAN route is exercised live-shaped on single-chunk runs; multi-chunk replan passes have a known re-entry limitation (KI-20). `sprint-loop.py` remains ~2,940 lines — the "God-script" flaw is deliberately deferred; the `sprint_loop/` package exists and extraction continues.

**KIs closed:** KI-18, KI-19 (reimplemented). **KIs filed:** KI-20. **Findings fixed:** N-1, N-4, N-5, N-8.

---

## Housekeeping

Once the PRs open, retire `factory/schema-v3-and-subagent-executor` with a comment pointing to this stack. The prompt files and reports under `planning/review-cleanup/` are the audit trail — each PR's find→fix story, the review rounds, the punch lists, and the frontier sign-off are all there.

**Deferred fast follows (future PRs):**
- N-3: checkpoint resume drops seat assignments (pre-existing; needs role reconstruction in `_main_inner` after `load_checkpoint`)
- N-6: `backends.py` dead duplicate dry-run block + hardcoded branch fallback
- N-7: `vocab.py` depth — plan-reviewer verdict line and `reached_phase_step` literals still hand-synced
- KI-20: multi-chunk replan re-entry fix
- KI-5, KI-13: remain OPEN (honestly documented)

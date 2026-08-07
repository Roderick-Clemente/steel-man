# Phase 3 — KNOWN-ISSUES (operational findings during execution)

## KI-1 — openai executor tier unavailable ("Exec failed", num_turns:0)

- **Symptom:** `droid exec --model gpt-5.4-mini` (and `gpt-5.4`) return
  `{"subtype":"failure","is_error":true,"num_turns":0,"result":"Exec failed"}`
  in ~1.2s with **0 tokens** across input/output/cache. No stderr output.
- **Scope:** openai family only. Confirmed working in the same environment and
  window: `claude-opus-5` (anthropic, ran the chunk-1 test-author),
  `grok-4.5` (xai), `gemini-3.1-pro-preview` (google), and `glm-5.2` (zhipu).
- **Distinguishing it from the Phase-2 autonomy gate (KI-1 there):** that gate
  produced `num_turns:0` with a message "Re-run with --auto medium/high". This
  failure has **no message and 0 duration of actual work** — it is a provider
  availability failure, not a permission gate. `--auto low` is not the cause
  (claude-opus-5 test-author succeeded at `--auto low`).
- **Persistence:** observed at ~02:24 and re-confirmed hours later; both
  `gpt-5.4` and `gpt-5.4-mini` fail identically. Not a transient rate-limit.
- **Impact:** the cheap/fast **executor** seat (plan model: `gpt-5.4-mini`) is
  blocked. Test-author and both validator seats are unaffected.
- **Decision (human, 2026-08-07):** initially **wait**; then, after the outage
  persisted for hours and re-probes confirmed it was not transient, the human
  **approved substituting `glm-5.2` (zhipu)** as the chunk-1 executor. The swap
  is §17.1-compliant (no hard family invariant binds the executor beyond
  separation) and preserves every separation: zhipu ≠ anthropic (test-author),
  ≠ xai/google (validators). No collision-guard trip; no validator swap needed.
  - **Outcome:** chunk 1 reached GREEN and **cross-family ACCEPT** (grok-4.5 +
    gemini-3.1-pro-preview, 0 findings) with the glm-5.2 executor.
  - **Posterity A/B (deferred):** when openai recovers, re-run the *same* locked
    chunk with `gpt-5.4-mini` as executor — identical tests + validators, only
    the executor family swapped — as a Phase-3.1 calibration data point (does a
    different-family executor change the diff or the validators' findings?).
  - The failed openai envelope is preserved at
    `phase-3/build-evidence/chunk1-executor-openai-failure-envelope.json`.

### Chunk 1 parked state — RESOLVED

Resolved by the glm-5.2 substitution above. All three chunks completed and
committed on `factory/phase-3-profile`; final suite 99 passed. The openai
re-probe was repeated once more before chunk 2 (still failing identically) and
the human authorized completing all remaining chunks on glm-5.2. Posterity A/B
against `gpt-5.4-mini` remains open for when openai recovers.

## KI-2 — validator seat has a write vector via `Execute` at `--auto high`

- **Symptom / risk:** the validator is nominally read-only, but it is invoked
  with `--enabled-tools Read,Glob,Grep,LS,Execute` and `--auto high` so it can
  run pytest. `Execute` at that autonomy can, in principle, mutate the working
  tree (write a file, stage, etc.). A validator that edits the code it is
  judging would void independence.
- **Mitigation (applied every chunk):** a `git status --porcelain` +
  `git diff --stat` **stray-write check** is run immediately after each
  validator run, before trusting the verdict. Across all six Phase-3 validator
  runs the tracked diff was unchanged (only the executor's intended files),
  i.e. no validator wrote to the tree.
- **Residual:** the guarantee is detective, not preventive. A cleaner design
  would give the validator a read-only test runner (execution without write) or
  run it against a throwaway checkout. Recorded for the review-tooling backlog.

## KI-3 — envelope does not surface `providerLock` / `apiProviderLock`

- **Symptom:** the `-o json` result envelope in this Droid CLI version contains
  `type/subtype/is_error/duration_ms/num_turns/result/session_id/usage` but
  **no `providerLock` / `apiProviderLock`** (PRD §17 expects them "in the result
  envelope"). No `droid exec` flag surfaces them (`--help` reviewed).
- **Impact:** the two provider-lock fields required by `telemetry/SCHEMA.md`
  cannot be recorded as *observed*. Per `commit-body-recipe.md` §13 ("...or the
  provider name if it is not yet known") they are set to the **known provider**
  for the pinned model (anthropic / zhipu / xai / google). This is attribution
  from the pinned `--model`, not an observed inner-session lock.
- **Note:** family-separation reasoning is unaffected — it keys on model family,
  which the pinned `--model` fixes regardless of the lock fields.

## KI-4 — telemetry `role` enum omits `test-designer`

- **Symptom:** `telemetry/SCHEMA.md` lists `role` as
  `planner / executor / validator / reviewer`, but PRD §7 defines **five** roles
  including **test designer** (the seat that authors + locks the failing test,
  separation `≠ executor family`). The enum has no value for it.
- **Handling:** Phase-3 `runs.jsonl` records the test-author runs with the
  canonical `role: "test-designer"` anyway. The schema enum should be extended
  to include it (and `reviewer` clarified as *plan* reviewer vs `validator` as
  *implementation* validator). Flagged for a SCHEMA.md `schema_version` bump.

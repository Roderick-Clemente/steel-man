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

### Chunk 1 parked state (resume point)

- **Test-author:** DONE. `claude-opus-5` wrote `test/test_profile_model.py`
  (3 tests, `@pytest.mark.models`, behavioral `getattr` guard). Envelope:
  `phase-3/build-evidence/chunk1-test-author-envelope.json`.
- **Valid-RED:** CONFIRMED (exit 1, "intended assertion ran and failed",
  assertion phrase `profile key-set equals contract` present).
- **Lock:** DONE. `phase-1/locks/test/test_profile_model.py.lock.json`,
  sha256 `8041e6073c42a367483a5ce4e4c984ffdb0e3acaa8ee147140b82afead88e79e`.
  Hook enforcement re-verified (Edit on the locked file → exit 2).
- **Executor:** BLOCKED on this issue. The one failed attempt touched nothing
  (`models.py` clean). Envelope:
  `phase-3/build-evidence/chunk1-executor-envelope.json` (failure record).
- **Resume:** when openai recovers, re-fire the chunk-1 executor call from
  `phase-3/RUN-COMMANDS.md`; the locked test and valid-RED still stand.

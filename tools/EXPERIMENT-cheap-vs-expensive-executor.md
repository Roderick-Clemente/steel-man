# Executor experiment results — cheap vs expensive model, full-cycle cost comparison

Run date: 2026-09-13
Arm A run id: `r-phase45-20260913-005223` (executor kimi-k3)
Arm B run id: `r-phase45-20260913-012823` (executor gpt-5.2)

---

## 1. Executive summary

In a single paired run (n=1 per arm), the data leans toward gpt-5.2 having lower total cost of ownership, but several confounds prevent a conclusive verdict. These are directional findings; the experiment will be rerun (≥3 runs per arm, KI-18 fixed so the locked suite is a true constant) before any confirmed result.

The clearest signal is the **executor-only** comparison: Arm B's gpt-5.2 cost **85,394 credits** across 13 turns (34,726 in / 6,339 out), while Arm A's kimi-k3 cost **371,917 credits** across 20 turns (63,623 in / 32,747 out) — a 4.4× gap. The underlying driver is output volume, not per-token price: kimi emitted 32,747 output tokens vs gpt's 6,339 (5.2× ratio) across more turns (20 vs 13) to produce a similar (actually smaller) diff. Credits = price-per-token × volume, and volume dominated.

On the full pipeline, Arm A totaled **1,077,891 credits** vs Arm B's **751,567**, but that headline carries two caveats (detailed in Section 7): (i) Arm A's gemini validator was manually re-run after an orchestration crash, inflating its cost by ~209K credits beyond Arm B's equivalent seat; excluding both gemini validator seats narrows the full-pipeline gap from ~30% to ~15%. (ii) KI-18 broke the controlled variable: Arm B's test-designer bounce replaced the 7-test locked suite with a 20-test suite that was never re-locked, so the two arms did not run against identical tests — this contaminates the lines-produced and code-quality comparisons in Sections 5 and 1.

On code quality, no defect was found by either validator in either arm; independent review of the two diffs is pending. Arm B's REJECT was purely procedural (a lock-manifest SHA mismatch after the test-designer bounce), not a code-quality judgment — grok explicitly said the implementation "looks criterion-complete."

**Run-to-run variance caveat.** The plan-reviewer seats received substantially identical inputs yet varied between arms: grok-4.5 cost 176,320 (Arm A) vs 128,100 (Arm B) credits; glm-5.2 cost 66,206 (Arm A) vs 128,299 (Arm B) credits. This ~38–94% variance on comparable-input seats is the noise floor a single run cannot rise above; the full-pipeline totals should be read with that in mind.

---

## 2. Full comparison table

| Cost component | Arm A (kimi-k3) | Arm B (gpt-5.2) |
|---|---|---|
| Executor turns | 20 | 13 |
| Executor tokens (in/out) | 63,623 / 32,747 | 34,726 / 6,339 |
| Executor credits | 371,917 | 85,394 |
| Executor duration | 561,774 ms | 96,326 ms |
| Validator 1 (grok) turns | 10 | 9 |
| Validator 1 tokens (in/out) | 49,840 / 18,551 | 92,415 / 8,989 |
| Validator 1 credits | 119,466 | 128,610 |
| Validator 1 verdict | ACCEPT-WITH-NITS | REJECT_TEST (lock mismatch, round 2) |
| Validator 2 (gemini) turns | 11 | 3 |
| Validator 2 tokens (in/out) | 273,114 / 11,627 | 65,216 / 5,710 |
| Validator 2 credits | 289,313 | 80,220 |
| Validator 2 verdict | ACCEPT | ACCEPT |
| Test designer turns | 0 (skipped) | 18 |
| Test designer credits | 0 | 146,924 |
| Lines produced | 578 insertions / 108 deletions | 764 insertions / 152 deletions |
| Files touched | 6 | 6 |
| Retry rounds | 0 | 1 |
| Test-designer bounces | 0 | 1 |
| **Total pipeline turns** | 60 | 73 |
| **Total pipeline credits** | 1,077,891 | 751,567 |

Notes on the table:

- **Validator 1 verdict (Arm A)** was `ACCEPT-WITH-NITS` (`ok: true`), not a bare `ACCEPT`. The nits were cosmetic; no code-quality defect was found.
- **Validator 1 verdict (Arm B)** is the **round-2** verdict. Round 1 also returned `REJECT_TEST` and triggered the test-designer bounce. The round-2 rejection was the lock-manifest SHA mismatch (KI-18), not a code-quality issue.
- **Retry rounds / Test-designer bounces** in Arm B are the same single event: one `REJECT_TEST` → test-designer rewrite. There were no `REJECT_IMPL` executor retries in either arm.

---

## 3. Per-seat cost breakdown

### Arm A (kimi-k3)

| Seat | Model | Turns | in_tok | out_tok | Credits | Duration |
|---|---|---|---|---|---|---|
| Planner | gemini-3.1-pro-preview | 2 | 26,928 | 6,704 | 54,669 | 40,760 ms |
| Reviewer 1 | grok-4.5 | 10 | 146,392 | 14,491 | 176,320 | 307,334 ms |
| Reviewer 2 | glm-5.2 | 7 | 52,769 | 14,754 | 66,206 | 160,263 ms |
| Test designer | — (skipped) | 0 | 0 | 0 | 0 | 0 |
| Executor | kimi-k3 | 20 | 63,623 | 32,747 | 371,917 | 561,774 ms |
| Validator 1 | grok-4.5 | 10 | 49,840 | 18,551 | 119,466 | 284,486 ms |
| Validator 2 | gemini-3.1-pro-preview | 11 | 273,114 | 11,627 | 289,313 | 132,420 ms |
| **Total** | | **60** | **612,666** | **98,874** | **1,077,891** | |

### Arm B (gpt-5.2)

| Seat | Model | Turns | in_tok | out_tok | Credits | Duration |
|---|---|---|---|---|---|---|
| Planner | gemini-3.1-pro-preview | 2 | 27,291 | 6,508 | 54,020 | 54,802 ms |
| Reviewer 1 | grok-4.5 | 10 | 64,509 | 15,595 | 128,100 | 302,269 ms |
| Reviewer 2 | glm-5.2 | 18 | 77,599 | 20,888 | 128,299 | 249,450 ms |
| Test designer | glm-5.2 | 18 | 71,797 | 33,486 | 146,924 | 358,348 ms |
| Executor | gpt-5.2 | 13 | 34,726 | 6,339 | 85,394 | 96,326 ms |
| Validator 1 | grok-4.5 | 9 | 92,415 | 8,989 | 128,610 | 156,438 ms |
| Validator 2 | gemini-3.1-pro-preview | 3 | 65,216 | 5,710 | 80,220 | 52,008 ms |
| **Total** | | **73** | **433,553** | **97,515** | **751,567** | |

Key observations:

- Arm B had **more total turns (73 vs 60)** but **fewer total credits (751,567 vs 1,077,891)**. Its turns were cheaper because the heavy-token seats (executor, gemini validator) did far less work.
- The two big deltas are the **executor** (Arm A +286K credits) and the **gemini validator** (Arm A +209K credits). The executor gap is an intrinsic efficiency signal; the gemini validator gap is confounded (see next bullet).
- Arm A's gemini validator gap is a manual-re-run artifact: its envelope shows `retry_count=1` and 273,114 input tokens (vs Arm B's 65,216), consistent with the post-crash manual re-run reading a much larger context. Excluding both gemini validator seats, the full-pipeline gap narrows from ~30% to ~15%. The executor-only comparison (4.4× in favor of gpt-5.2) is the cleanest signal this run provides.
- **Run-to-run variance caveat.** The plan-reviewer seats (which received substantially identical inputs) varied between arms: grok-4.5 cost 176,320 (Arm A) vs 128,100 (Arm B) credits; glm-5.2 cost 66,206 (Arm A) vs 128,299 (Arm B) credits. This ~38–94% variance on comparable-input seats is the noise floor a single run cannot rise above.

---

## 4. Validator verdict analysis

### Arm A

- **grok-4.5 — `ACCEPT-WITH-NITS`.** Verified evidence integrity (commit SHA and lock SHA match, locked 7/7 passed, regression 36/36 passed, no security findings), confirmed scope was confined to the allowed files, and walked all seven spec criteria as satisfied. Findings were nits only (one low-severity `F-homes-store-1`). Concluded GREEN evidence is intact and the implementation matches the locked plan.
- **gemini-3.1-pro-preview — `ACCEPT`.** Praised test quality ("asserts against the contract through public service interfaces … avoids conditional assertions"), confirmed GREEN-evidence integrity (lock SHA matches, 7 locked + 36 regression pass), and confirmed spec conformance. Its only nit: `HomeService._ensure_default_home`'s `if not self._cache.get_homes()` is functionally dead code because `CacheService` self-initializes the default home on empty load — "harmless, does not affect correctness."

**Agreement:** both accepted; grok was stricter (nits + a low-severity finding), gemini was clean plus an `info`-severity dead-code note. Neither caught a bug the other missed. No validator found a defect.

### Arm B

- **grok-4.5 — `REJECT_TEST` (round 2).** This was **not** a code-quality judgment. Grok confirmed evidence integrity except one thing: `locked_test_sha_observed` (`806a9855…`) did not match the lock-manifest SHA (`fd2f24ba…`). Checklist item 3 requires a match; "Accept is forbidden on that ground alone, regardless of green counters." It explicitly stated: "Against the on-disk redesigned suite, **the implementation looks criterion-complete**," and "That does not authorize ACCEPT while the lock identity is broken." Root cause: after round 1's `REJECT_TEST` redesign, the replacement test (20 tests) was **not re-locked** — the manifest still pointed at the pre-redesign SHA.
- **gemini-3.1-pro-preview — `ACCEPT`.** Reviewed spec conformance, test quality, GREEN-evidence integrity, and no-regression all as passing, and issued a clean ACCEPT. It did **not** flag the lock-manifest SHA mismatch that grok caught.

**Agreement:** the validators diverged, but only on process integrity. Grok caught a real framework defect (the un-re-locked test) that gemini missed; on the code itself they both judged it acceptable. The gate fail-closed on the split. Note: Arm B's validators reviewed code written against a 20-test suite (post-redesign) while Arm A's reviewed code against the original 7-test suite (KI-18), so the two verdict sets are not directly comparable on code quality.

---

## 5. Code quality comparison

### Files touched (identical set in both arms)

1. `backend/app/models/__init__.py`
2. `backend/app/models/home.py` (new)
3. `backend/app/services/__init__.py`
4. `backend/app/services/cache_service.py`
5. `backend/app/services/home_service.py` (new)
6. `backend/app/services/layout_service.py`

### Lines

| | Arm A | Arm B |
|---|---|---|
| Files changed | 6 | 6 |
| Insertions | 578 | 764 |
| Deletions | 108 | 152 |

\* **KI-18 caveat on lines comparison.** Arm B ran against a 20-test redesigned suite while Arm A ran against the original 7-test suite. The larger test surface may have driven the larger diff (764 vs 578 insertions); this comparison is contaminated until the experiment is rerun with the locked suite as a true constant.

Full diffs are saved for operator review:
- `~/work/experiment-evidence/arm-a-diff.txt`
- `~/work/experiment-evidence/arm-b-diff.txt`

### Architectural approach

Both executors solved the problem the same way at a high level — a new `Home` model plus a `HomeService` wrapper over the existing `CacheService`/`LayoutService`, adding optional `home_id` parameters so legacy no-arg call sites keep working against a single default home. The differences are in how much scaffolding each added:

- **Arm A (kimi, smaller diff):** A minimal `Home(home_id, name)` model (no timestamp) with module-level constants `DEFAULT_HOME_ID = "default"` / `DEFAULT_HOME_NAME`. `HomeService` wraps `CacheService`/`LayoutService` privately and does two things on init: `_ensure_default_home()` and `_persist_legacy_upgrades()`. Missing-home reads return an empty list, with `home_exists()` as the named distinguishable signal. Uses classic `Optional` typing and a simple positional constructor.
- **Arm B (gpt, larger diff):** A richer `Home(home_id, name, created_at)` model, plus three extra dataclasses/exception types (`HomeNotFound`, `DeleteResult`, and the `HomeNotFoundRead` dataclass that carries a named not-found signal for reads). Its constructor is far more defensive, accepting several alternate keyword spellings (`layout_config_file`, `device_cache_file`, `cache_path`, `layout_path`, `data_dir`, `**_ignored`). It uses `from __future__ import annotations` and `dataclasses`.

### Structural differences for the operator to review

- **Criterion 9 resolution differs.** Arm A signals a missing home via `home_exists()` plus an empty-list read; Arm B introduces a dedicated `HomeNotFoundRead` dataclass so a missing home is a named, distinguishable return value rather than a bare empty list. Both were accepted; they are genuinely different semantic choices.
- **Constructor surface.** Arm B's `HomeService.__init__` accepts many alias spellings and a `data_dir` expansion — more tolerance but more surface to test and maintain. Arm A's is single-spelling and minimal.
- **Model shape.** Arm B adds `created_at`; Arm A does not. This is extra state the spec did not appear to require.
- **Defensive scaffolding.** Arm B's `DeleteResult`, `HomeNotFound`, and `HomeNotFoundRead` types are explicit return/exception contracts; Arm A leans on `home_exists` + dict results. Arm B's `cache_service.py` (+385 lines) and `home_service.py` (+238) are the largest single files; Arm A's are +285 and +147 respectively.

### Code quality assessment

No defect was found by either validator in either arm; independent review of the two diffs is pending. The "no defects" signal rests on two validators (who disagreed procedurally on Arm B) finding no bugs — it is not a confirmed parity claim. Additionally, Arm B's code was written against a 20-test redesigned suite (KI-18) while Arm A's was written against the original 7-test suite, so the two implementations were not tested under identical conditions.

---

## 6. Outcome determination

The three hypotheses were:

1. **kimi wins on total cost** — cheap executor hypothesis holds
2. **gpt-5.2 wins on total cost** — hypothesis busts
3. **Costs are similar** — executor model doesn't matter much

**Directional result: the data leans toward hypothesis 2, but a single run with known confounds cannot confirm it.**

- **Executor-only cost:** Arm A 371,917 vs Arm B 85,394 credits (~4.4×). kimi emitted 32,747 output tokens vs gpt's 6,339 across 20 vs 13 turns, and produced *fewer* net lines (578 vs 764 insertions). The cheap model's per-token advantage was swamped by its output volume and turn count.
- **Full-pipeline cost:** Arm A 1,077,891 vs Arm B 751,567 credits (~30% headline gap). Excluding the confounded gemini validator seats (~209K delta from a manual re-run), the gap narrows to ~15%. Arm B absorbed a 146,924-credit test-designer bounce that Arm A never hit and still came out cheaper.
- **Run-to-run variance:** Plan-reviewer seats with comparable inputs varied ~38–94% between arms (Section 3). A single run cannot separate signal from noise at that level.

**The sharper transferable insight:** credits = price-per-token × volume, and **volume dominated**. kimi-k3 produced 32,747 output tokens across 20 turns; gpt-5.2 produced 6,339 across 13 turns — a 5.2× output ratio that swamped any per-token price advantage. The "cheap executor" hypothesis was ill-posed: it assumed executor cost was primarily a function of model price tier, when it was primarily a function of output efficiency. A "cheap" model that talks five times as much is not cheap.

**Rerun plan.** Before any confirmed verdict: ≥3 runs per arm, KI-18 fixed so the locked suite is a true constant across arms, and the gemini validator re-run confound eliminated. The executor-only signal (4.4× in favor of gpt-5.2) is strong enough to justify the rerun; it is not strong enough, from n=1, to confirm.

---

## 7. Framework health

- **KI-10 (rendered validator prompts) — HELD.** All four validator reports reference concrete file contents and line numbers (e.g., gemini quoted `home_service.py:210-216`; grok quoted the lock manifest and `fd2f24ba…`). No placeholder artifacts appeared in any `finding_text`.
- **KI-15 (regression `full_suite` evidence) — HELD.** Both bundles carry `tests.full_suite` with real counts and a real command: Arm A 36 passed / 0 failed, Arm B 49 passed / 0 failed, both `suite_exit_code=0`. The counts are not inferred from locked-test counters.
- **KI-16 (executor retry feedback) — DID NOT FIRE.** Neither arm took a `REJECT_IMPL` → executor retry (Arm A `retry_count=0`; Arm B's `retry_count=1` was a `REJECT_TEST` → test-designer bounce). There was no executor-retry round in which to exercise feedback rendering, so KI-16 remains unproven live.
- **REJECT_TEST routing — WORKED.** Arm B round 1's `REJECT_TEST` correctly routed to the test-designer (glm-5.2), which rewrote the test (7 → 20 tests).
- **New finding (KI-18): the test-designer bounce does not re-lock the redesigned test.** After the redesign, the lock manifest still recorded `fd2f24ba…` while the on-disk suite was `806a9855…` (20 tests). This made round 2's SHA cross-check fail in grok's eyes and forced a fail-closed REJECT that was *not* about code. This is a framework defect to fix: after a test-designer rewrite is accepted, the manifest must be re-generated so the redesigned test is the lock.
- **Validator orchestration transient crash (Arm A).** The pipeline reached validators but `orchestrate-review.py` exited 1; the 300-char stderr truncation hid the root cause. Validators were re-run manually and both accepted. Diagnosed as environmental and not reproducible. Operator action item: lift the 300-char stderr truncation so future transient failures leave a diagnosable trace. **Cost impact on the full-pipeline comparison:** Arm A's gemini validator cost 289,313 credits (273K input tokens, `retry_count=1`) vs Arm B's 80,220 credits (65K input tokens) — a ~209K delta attributable to the re-run, not to the executor choice. Full-pipeline totals excluding gemini validator seats: Arm A 788,578 vs Arm B 671,347 (~15% gap, down from the ~30% headline).
- **Experimental-integrity note.** The "same locked tests" controlled constant did not hold for Arm B: its test-designer bounce silently replaced the 7-test locked suite with a 20-test suite that was never re-locked. Arm A ran the original 7 locked tests; Arm B effectively ran a different, larger test. KI-18 is therefore also an experiment-validity issue, not just a pipeline cosmetic bug.

---

## 8. Reference comparison (attempt 10 context)

| Seat | Attempt 10 credits | Arm A credits | Arm B credits |
|------|-------------------|---------------|---------------|
| Planner | 73,496 | 54,669 | 54,020 |
| Reviewer 1 (grok) | 187,316 | 176,320 | 128,100 |
| Reviewer 2 (glm) | 69,168 | 66,206 | 128,299 |
| Test designer | 0 (skipped) | 0 | 146,924 |
| Executor | 236,792 | 371,917 | 85,394 |
| Validator 1 (grok) | 164,759 | 119,466 | 128,610 |
| Validator 2 (gemini) | 235,217 | 289,313 | 80,220 |
| **Total** | **~967K** | **1,077,891** | **751,567** |

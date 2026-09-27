# REPORT — Final frontier review of the review-cleanup stack (post-punch-list)

Reviewer: final holistic pass over the 7-PR stack (`factory/v3-telemetry-schema` →
`factory/plan-defect-route`), per `PROMPT-FINAL-frontier-review.md`, **after**
the punch list (`PROMPT-FINAL-punchlist.md`) was applied to the stack top.
Date: 2026-09-13. Base: `main` @ `7b6f82f`. Stack top: `a5f0cfb`.
The prior review (findings N-1 through N-7) is preserved in history at commit
`8fcb104`.

---

## 1. Stack integration verdict

**PASS.**

- Topology re-verified: each branch is an ancestor of the next, all 7 based on
  `main` HEAD (`7b6f82f`), every local branch in sync with `origin/`.
- Branches 1–6 are **byte-identical to the previously reviewed SHAs**
  (`71ccc97`, `54b9979`, `b530f33`, `96d6f9e`, `1da4ed8`, `62f786a`); the punch
  list landed as 4 commits on branch 7 only (`77c6ae6`, `8fcb104`, `4a35da3`,
  `a5f0cfb` on top of `5b80a1c`), so no downstream rebase was needed and none
  happened.
- Full suite re-run on **every branch 1→7** (system Python 3.9.6 / pytest
  8.4.2): all seven green except the one known environmental failure,
  `tests/test_sign_chunk_token.py::test_replay_chunk13_succeeds` (duplicated
  local git history; pre-existing, present on every branch). Branch 7 tally:
  **498 passed, 3 skipped (documented), 1 failed (known env)** — the +2 over
  the prior pass are the punch list's new tool-allowlist tests.
- Not run: `ruff` / `mypy` (not installed in this environment). CI should
  cover these on push.
- The prior pass's integration-only gap (multi-chunk replan re-entry) is now
  **on record as KI-20** with status OPEN, three fix directions, and an honest
  decision note. The dry-run e2e suite remains structurally unable to see it;
  the pilot's actual (single-chunk) use case is unaffected.

---

## 2. P1 fix verification

The punch-list diff (`5b80a1c..a5f0cfb`) touches **zero** of the P1-fix
surfaces (`per_chunk.py`, `vocab.py`, `orchestrate-review.py`, `valid-red.py`,
prompts), so the prior verifications carry over byte-identical. Summary:

### 2.1 KI-16 dead retry path — **CONFIRMED FIXED**

`run_chunk_inner` relaxes the RED gate for
`verify_mode or redesign_round or implementation_retry_round` (the latter
`rejection_kind == REJECTION_IMPLEMENTATION`), confirms GREEN via
`verify_green` rather than waiving the gate, and the rejecting validator's
finding threads `classify_rejection` →
`format_implementation_rejection_feedback` → `chunk.rejection_feedback` →
`render_executor_prompt` `{{prior_implementation_rejection}}` → executor.md.
Pinned by
`test_reject_impl_feedback.py::test_live_reject_impl_retry_crosses_real_red_gate_with_finding`,
which drives the real lock / valid-red / verify-green / evidence gates.

### 2.2 REPLAN verdict — **CONFIRMED FIXED (implemented for real in PR 7)**

`vocab.py` is the single source (`VERDICT_REPLAN`, `tagged_line_pattern`,
longest-first, anchored, last-match); validator.md's six-verdict block is
contract-tested verbatim against the vocab tuple;
`step4_parse_verdicts` takes the last tagged line; `step6_gate_decision`
blocks on REPLAN; `classify_rejection` returns `"plan"` (REPLAN dominates
mixed panels); `run_chunk_with_retries` charges `rs.replans_spent`, archives
evidence, and hands the finding to the outer loop. Exit 7 on budget
exhaustion; budget survives checkpoint resume (sentinel-tested).

### 2.3 Warnings-summary misclassification (KI-17) — **CONFIRMED FIXED**

`valid-red.py::outside_failures_region` excludes warnings-summary sections
and `FAILED` short-summary lines from the fallback signature scan;
structure-first KI-9 ordering intact; pinned by
`tests/test_valid_red_structure.py`.

---

## 3. Punch-list verification (N-1, N-2, N-4, N-5)

All four punch-list items were applied correctly; each was verified against
the diff and the live code paths, not the commit messages.

### N-1 [P1] — **FIXED and verified on the live path** (`77c6ae6`)

- `_main_inner::_make_role` now derives every seat's allowlist from
  `DEFAULT_ENABLED_TOOLS[role]`; all hardcoded literals are gone, including
  the validator seat construction. `run_planner` (sprint-loop.py:621) passes
  `rs.planner.enabled_tools` → now `Read,Glob,Grep,LS` — **the KI-7 fix
  finally reaches `droid exec` on the live default path.** The plan-reviewer
  seat (line 876) derives the same way.
- The fix went one correct step beyond the instruction: the dict itself
  granted `ApplyPatch` to executor/test-designer, an id the installed CLI
  (droid 0.197.0, `--list-tools`) does not register — shipping it live would
  have reintroduced KI-2's 0-byte-envelope rejection. The dict is corrected
  to the verified set (`Read,Glob,Grep,LS,Edit,Create,Execute`), so the
  single source now holds only ids the CLI accepts, and the prompt
  `{{enabled_tools}}` rendering (per_chunk.py:1031/1085) advertises exactly
  what the seat gets.
- Validator subtlety checked: the seat record now carries the dict value
  (`Read,Glob,Grep,LS,Execute`), but the bundle-mode **invocation**
  (`per_chunk.run_validators`, line 636) keeps its deliberate, commented
  `"Read,Glob,Grep,LS"` KI-2/§17.5 policy pin — fail-closed, no live
  behavior change.
- Pin verified: `test_planner_no_execute.py` now drives `main()` end to end
  in `--dry-run` and asserts on the RunState the entrypoint actually
  constructs (planner without Execute, every seat equal to its dict value, no
  ApplyPatch/MultiEdit anywhere), plus a structural test pinning the dict to
  the verified id set. Against the old literal the planner assertion fails.

### N-2 [P2] — **FILED as KI-20, accurately** (`8fcb104`)

The KNOWN-ISSUES entry matches the traced defect exactly: replan pass
re-derives every chunk from index 0 → accepted chunk GREEN at HEAD →
"Invalid RED: test passed" → relaxation inapplicable (fresh chunk, empty
`rejection_kind`) → `RED_REJECTED` retry → budget exhaustion → exit 3. It
records why the dry-run single-chunk e2e cannot see it, the three fix
directions from the review, and an honest file-don't-rush decision. The PR 7
body recommendation now states the validation envelope with the KI reference.

### N-4 [P2] — **FIXED** (`4a35da3`)

Scorecard now reads 20 found, 14 fixed (KI-18 added), 3 open (KI-5, KI-13,
KI-20), 1 partially fixed (KI-14), 1 limitation (KI-12), 1 withdrawn (KI-6) —
arithmetic checks (14+3+1+1+1 = 20) and every status matches KNOWN-ISSUES.md.
The attempt-11 row and the "Upcoming" experiment section are rewritten as
completed with the PR 5 run ids and the honest KI-16-remained-unproven note.
One residual nit: see N-8.

### N-5 [P3] — **FIXED** (`a5f0cfb`)

All three occurrences now read "~38–94%", matching the data
(grok-4.5: 48,220/128,100 ≈ 38%; glm-5.2: 62,093/66,206 ≈ 94%). Note the
correction lands on the PR 7 branch while the doc is introduced in PR 5, so
PR 5 as opened will briefly show the stale range — an accepted stacked-PR
trade-off (no downstream rebase), worth a sentence in PR 5's body.

### Deferred items — properly documented, nothing silently dropped

N-3 (resume drops seat assignments), N-6 (backends.py dead block + branch
literal), and N-7 (vocab depth: plan-reviewer verdict line, phase-step
literals) are recorded as fast follows in `REPORT-FINAL-punchlist.md` and in
the prior review (in history); KI-20's multi-chunk fix awaits its own design
pass. KI-5 and KI-13 remain OPEN and honestly documented. The punch-list
commits touched nothing outside their stated scope (7 files, verified by
diff stat).

---

## 4. New findings

### [P3] N-8 — RUN-LEDGER internal denominator inconsistency

The reconciled scorecard says "**20** known issues found (KI-1 through
KI-20)", but the "KI-7 shape" section in the same file says "Four of the
**nineteen** issues share the same structural defect." KI-20 joined the
ledger one commit earlier, so the denominator should be twenty (the four
instances themselves are unchanged — KI-20 is not KI-7-shaped). One-word doc
fix; the punch list executed its prescribed text ("sixteen" → "nineteen"),
which was written before KI-20 was added to the count.

No other new findings. The punch-list commits introduce no regressions: the
suite is green on the new HEAD, the P1-fix surfaces are untouched, and the
one behavioral change (seat allowlists) is covered by a test that drives the
real entrypoint.

---

## 5. Quality assessment

**Capstone-ready. Open the PRs.**

The stack now holds together end to end: the three original P1s are fixed
with tests that exercise real gates; the fourth P1 found in final review
(N-1) is fixed at the stack top with an entrypoint-level test that would have
caught the original defect; the one known design gap (multi-chunk replan
re-entry) is filed as KI-20 with fix directions instead of being papered
over; the ledger, experiment doc, and KNOWN-ISSUES now tell one consistent
story. The honesty discipline is the standout: "filed, not fixed … filing
honestly beats shipping an untested multi-chunk fix under time pressure" is
exactly the record AGENTS.md asks for.

Worth doing, none blocking:
1. The N-8 one-word fix ("nineteen" → "twenty") — trivially foldable into any
   PR 7 touch-up.
2. A sentence in PR 5's body noting the variance range is corrected at the
   stack top (PR 7).
3. The deferred fast follows (N-3, N-6, N-7, KI-20 fix) as follow-up PRs
   after the stack lands.
4. Retire `factory/schema-v3-and-subagent-executor` with a pointer to the
   stack once the PRs open.

Commit history: the four punch-list commits keep the standard — conventional
prefixes, bodies that explain why and name the finding ids and KIs, co-author
trailers, no sensitive content. The N-1 commit body documenting the
verified-against-the-CLI ApplyPatch decision is a model commit message.
Pre-existing observation stands: sprint-loop.py remains ~2,940 lines (the
"God-script" flaw, deliberately deferred — say so in PR 7's body), and the
experiment doc's absolute local evidence paths are machine-specific pointers
in a public repo.

---

## 6. PR body recommendations

**PR 1 — `factory/v3-telemetry-schema`**: Declares telemetry schema v3 and
makes the docs match the emitters: front matter v2→v3 with a full migration
note, the `overridden` disposition documented, validator rows stamped with the
real branch instead of a hardcoded literal, phase enums aligned with what the
runner actually writes, and a dead success-path guard removed. Additive for
readers; v1/v2 rows unchanged.

**PR 2 — `factory/planner-integrity`**: Makes the planner seat's inputs and
outputs trustworthy: the plan is the seat's final message (validated
structurally, KI-7), planned against the operator's authored chunk contract
(KI-8), reviewed in a loop whose evidence is round-indexed so no round
overwrites the text a verdict hash-binds to. Checkpoint save/load becomes
field-driven for RunState and ChunkState, so future fields round-trip by
construction. Also implements the `ACCEPTED_ASSERTION` parse the test-designer
prompt promised. (The KI-7 tool-policy claim is completed at the stack top:
PR 7's `77c6ae6` makes the live entrypoint derive seat allowlists from
`DEFAULT_ENABLED_TOOLS`.)

**PR 3 — `factory/red-structural-classification`**: The RED gate classifies on
pytest's structural evidence (collected count, ERRORS vs FAILURES, exit code)
instead of substring-matching the whole blob, so a test that explains its own
RED is no longer punished (KI-9) and a warnings summary naming conftest.py no
longer reads as a collection failure (KI-17, renumbered with an in-file note).
The evidence producer's timeout is now a shared budget that exceeds every inner
step.

**PR 4 — `factory/rejection-routing-and-feedback`**: Rejections now route to
the seat that can act on them, carrying the rejecting validator's own finding:
REJECT_TEST re-fires the test-designer on its own bounded budget, and a
REJECT_IMPLEMENTATION retry reaches the executor with the finding rendered into
its prompt instead of dying at the RED gate (KI-16). Adds
`sprint_loop/vocab.py` as the single source for verdict/signal strings with
contract tests binding prompt, parser, and routing; refuses all-skipped or
zero-collected regression runs as green evidence; and parses the executor's
final `RESULT:` line only (SPEC_OR_TEST_BLOCKED → distinct exit 6).

**PR 5 — `factory/executor-experiment-docs`**: Documents the two-arm executor
experiment and reframes its claims to what n=1 supports: the 4.4× executor-only
credit gap is the clean signal, the full-pipeline headline is caveated by a
quantified ~209K validator re-run confound (~30% → ~15%) and the KI-18
broken-constant, and the transferable finding — output volume dominates price
tier — leads the conclusion. Reconciles the run ledger and files KI-18. (The
reviewer-variance range is corrected to ~38–94% at the stack top, PR 7.)

**PR 6 — `factory/runner-hygiene`**: Cleanup with no behavior change: removes
the dead shadowed `main()`, extracts the force-accept disposition into one
helper, consolidates test fixtures into shared conftest helpers, renders seat
tool lists in prompts from `DEFAULT_ENABLED_TOOLS`, and aligns the planner's
PLAN_HASH footer with the verbatim-hashing behavior.

**PR 7 — `factory/plan-defect-route`**: Implements the plan-defect route KI-19
removed as unsupported: `VERDICT: REPLAN` is back as a first-class verdict
driven by vocab.py end to end (prompt block, gate parser, routing), stopping
the chunk fail-closed, archiving the rejecting evidence, threading the finding
into the next planner prompt, and re-deriving the chunk list — bounded by
`--replan-budget` (default 1) with exhaustion exiting 7, and the budget
surviving checkpoint resume. Also pins the KI-18 re-lock with an end-to-end
lock.py regression, and carries the final-review punch list: live seat
allowlists derived from `DEFAULT_ENABLED_TOOLS` (KI-7 completed on the live
path, ApplyPatch drift corrected against the installed CLI), KI-20 filed, and
the ledger/experiment docs reconciled. Validation envelope stated honestly:
exercised live-shaped on single-chunk runs; multi-chunk replan passes have a
known re-entry limitation (KI-20).

**Housekeeping once the PRs open:** retire
`factory/schema-v3-and-subagent-executor` with a pointer to this stack (the
prompt files and reports under `planning/review-cleanup/` are the audit trail).

---

## Appendix — verification log (this pass)

- Ancestry + origin sync re-verified; branches 1–6 SHA-identical to prior
  pass; branch 7 = `5b80a1c` + 4 punch-list commits, local == origin.
- Test runs: full suite on all 7 branches; only the known chunk-13 env
  failure + 3 documented skips everywhere. Branch 7 (`a5f0cfb`):
  498 passed / 3 skipped / 1 failed (known env).
- `git diff 5b80a1c..a5f0cfb --stat`: 7 files, all within punch-list scope;
  zero lines touched on P1-fix surfaces (per_chunk.py, vocab.py,
  orchestrate-review.py, valid-red.py, prompts).
- N-1: read `77c6ae6` in full; traced `run_planner` (line 621) and
  plan-reviewer (line 876) consuming derived `enabled_tools`; confirmed
  `run_validators` keeps the commented §17.5/KI-2 no-Execute invocation pin
  (per_chunk.py:636); confirmed prompt rendering (per_chunk.py:1031/1085)
  reads the corrected dict; read the new entrypoint-level test.
- N-2: read the KI-20 entry against the prior pass's live-path trace —
  symptom, test-blindness explanation, and fix directions all match.
- N-4: recomputed scorecard arithmetic (14+3+1+1+1 = 20); cross-checked every
  named KI status against KNOWN-ISSUES.md; found the N-8 denominator nit.
- N-5: recomputed both variance endpoints (48,220/128,100 ≈ 38%;
  62,093/66,206 ≈ 94%); confirmed all three occurrences updated.
- Deferrals: confirmed N-3/N-6/N-7 + KI-20 fix documented in
  REPORT-FINAL-punchlist.md; confirmed KI-5/KI-13 still marked OPEN.

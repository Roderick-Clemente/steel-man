# Punch list report — final frontier review fixes (N-1, N-2, N-4, N-5)

Date: 2026-09-13

## Branch

- Branch: `factory/plan-defect-route` (stack top; all fixes land as
  additional commits — no downstream rebase needed).
- Scope: local only. Nothing was pushed and no pull request was opened.
- Protected pre-existing untracked `*.orig` files and `evidence/`
  directories were not modified.
- Chain-of-custody note: `planning/review-cleanup/REPORT-FINAL-frontier-review.md`
  had never been committed; the N-2 commit tracks it (with its updated
  PR 7 body recommendation) so the audit trail the punch list edits is
  in history.

## What was done

### N-1 [P1] — KI-7 fix now reaches the live path

`_make_role` in `tools/sprint-loop.py::_main_inner` now derives every
seat's allowlist from `DEFAULT_ENABLED_TOOLS[role]`; the hardcoded
literals are deleted, including the validator seat construction. The
prompt `{{enabled_tools}}` rendering and the live `droid exec`
invocation now share one source of truth, so a seat can only be handed
tools its prompt advertises.

One correction beyond the literal instruction, made after verifying
reality rather than trusting the dict: the dict granted `ApplyPatch` to
executor/test-designer. The installed CLI (droid 0.197.0,
`droid exec --list-tools`) has no `ApplyPatch`, `MultiEdit`, or `Write`
in its registry — `Read,Glob,Grep,LS,Edit,Create,Execute` are the valid
ids — and the CLI's "Unknown tool identifier(s)" path rejects unknown
ids wholesale (KI-2's exact 0-byte-envelope mechanism, still present in
the 0.197.0 binary). Shipping `ApplyPatch` into live invocations would
have reintroduced KI-2; instead `DEFAULT_ENABLED_TOOLS` itself is
corrected to the verified set, so the single source holds only ids the
CLI accepts. The validator seat record now carries the dict value
(`Read,Glob,Grep,LS,Execute`) as the punch list prescribes; the
bundle-mode validator *invocation* (`per_chunk.run_validators` →
`LocalBackend.validate`) keeps its deliberate no-Execute KI-2 policy
literal, which is a separate surface from the seat allowlist and
outside the punch list's `_main_inner` scope.

Pin: `tests/test_planner_no_execute.py` now drives `main()` end to end
in `--dry-run` (no droid calls; same fixture shape as the sprint-loop
dry-run e2e) and asserts on the RunState the entrypoint actually
constructs: planner without `Execute`, every seat exactly equal to its
`DEFAULT_ENABLED_TOOLS[role]` value, and no `ApplyPatch`/`MultiEdit`
anywhere. Against the old planner literal the assertion fails. A new
structural test pins the dict to the verified id set. (Test-implementation
note: the state is read off the loaded runner module, not `runpy` —
runpy returns a derived namespace that `main()`'s globals do not write
back into.)

### N-2 [P2] — KI-20 filed; PR 7 body states the validation envelope

`tools/KNOWN-ISSUES.md` gains KI-20: "REPLAN route validated on
single-chunk runs; multi-chunk replan pass re-runs accepted chunks and
fails their RED gate." Status: OPEN, severity: design gap. The entry
documents the traced live sequence (accepted chunk GREEN at HEAD →
"Invalid RED" → relaxation inapplicable → `RED_REJECTED` retry →
budget exhaustion → exit 3), why the dry-run single-chunk e2e tests
cannot see it, and the three proposed fix directions (record accepted
chunk ids; extend the GREEN relaxation to replan-pass chunks; skip
chunks whose scope is unchanged in the revised plan), with the
decision to file rather than ship an untested multi-chunk fix.

The PR 7 body recommendation in `REPORT-FINAL-frontier-review.md` now
reads "exercised live-shaped on single-chunk runs; multi-chunk replan
passes have a known re-entry limitation (KI-20)".

### N-4 [P2] — RUN-LEDGER reconciled

- Fixed count 13 → 14 (KI-18 added to the fixed list); open count
  3 → 2 (KI-5, KI-13).
- "Four of the sixteen issues" → "four of the nineteen issues".
- The "Upcoming: two-arm executor experiment" section is rewritten as
  completed, citing the PR 5 run ids (Arm A `r-phase45-20260913-005223`,
  Arm B `r-phase45-20260913-012823`) and the directional n=1 result,
  no longer gated on attempt 11; the attempt-11 table row is closed
  with the same facts (KI-16 remained unproven live; KI-18 found in
  Arm B, since fixed).
- KI-20 joins the scorecard: 20 found, 14 fixed, 3 open (KI-5, KI-13,
  KI-20).

### N-5 [P3] — variance range corrected

All three occurrences of the run-to-run variance range in
`tools/EXPERIMENT-cheap-vs-expensive-executor.md` (executive summary,
per-seat observations, outcome section) now read "~38–94%" — grok-4.5
is 48,220/128,100 ≈ 38%, not ~50%; glm-5.2 stays ≈ 94%.

## Commits (oldest first)

1. `77c6ae6 fix(planner): derive live tool allowlists from DEFAULT_ENABLED_TOOLS (KI-7, N-1)`
2. `8fcb104 docs: file KI-20 (multi-chunk replan re-entry limitation)`
3. `4a35da3 docs: reconcile RUN-LEDGER after KI-18 close and KI-20 file (N-4)`
4. `a5f0cfb docs: correct reviewer-variance range in experiment doc (N-5)`

## Validation

Required command:

```text
/usr/bin/python3 -m pytest -q
1 failed, 498 passed, 3 skipped
```

The sole failure is the permitted environmental failure
`tests/test_sign_chunk_token.py::test_replay_chunk13_succeeds` (local
git history contains two commits with the fixture subject; pre-existing
and present on every branch). The 3 skips are the pre-existing
`tests/test_layout_paths.py` overrides.

Confirmation with only that test deselected:

```text
/usr/bin/python3 -m pytest -q \
  --deselect tests/test_sign_chunk_token.py::test_replay_chunk13_succeeds
498 passed, 3 skipped, 1 deselected
```

## Blockers and deferrals

- Blockers: none.
- Deferrals (by the punch list's own scoping): N-3 (checkpoint resume
  drops seat assignments), N-6 (backends.py dead duplicate + hardcoded
  branch fallback), and N-7 (vocab.py depth) remain future-PR fast
  follows; the KI-20 multi-chunk replan fix is filed and awaits its own
  design pass. KI-16's live executor-retry feedback remains unproven
  (no REJECT_IMPL retry has fired in any recorded run).

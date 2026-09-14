# PR 6 Report — hygiene sweep

**Branch:** `factory/runner-hygiene`
**Base:** `factory/executor-experiment-docs`
**Commits:** 5 (one per spec item, in spec order)

---

## Per-item diffstat

| # | Item | Files | Diffstat |
|---|---|---|---|
| 1 | remove dead shadowed `main()` + orphaned help helper | `tools/sprint-loop.py` | 1 insertion, 55 deletions |
| 2 | extract force-accept disposition helper | `tools/sprint-loop.py` | 66 insertions, 76 deletions |
| 3 | shared conftest fixtures + migrate 3 suites | `tests/conftest.py`, `tests/test_reject_impl_feedback.py`, `tests/test_reject_test_routing.py`, `tests/test_spec_blocked_signal.py` | 244 insertions, 290 deletions |
| 4 | render seat tool lists from `DEFAULT_ENABLED_TOOLS` | `tools/sprint_loop/per_chunk.py`, `tools/sprint_loop/prompts/executor.md`, `tools/sprint_loop/prompts/test-designer.md`, `tests/test_sprint_loop.py` | 8 insertions, 4 deletions |
| 5 | align planner `PLAN_HASH` footer wording | `tools/sprint_loop/prompts/planner.md` | 4 insertions, 1 deletion |

---

## Item details

### 1. Dead `main()` removal

Deleted the first (shadowed, `noqa: F811`) `main()` in `tools/sprint-loop.py`
and its now-unused `_format_build_config_help()` helper. Help rendering is
already owned by the surviving `_main_inner()` via
`_format_build_config_help_synthetic()`, so no behavior was folded — the
dead block never ran. Removed the stale `# noqa: F811` from the surviving
entrypoint.

### 2. Force-accept disposition extraction

Extracted the duplicated ~35-line force-accept disposition block (the two
copies already diverged on checkpoint writing) into
`_apply_force_accept_disposition(rs, exit_code, force_accept_reason,
checkpoint_path)`. Checkpoint behavior is now explicit: the unattended
gate-auto-decide path passes the checkpoint path; the interactive
`accept` path passes `None`. Both call sites share the same disposition
build, telemetry rows, and stderr rendering.

### 3. Shared test fixtures

Added `tests/conftest.py` with `_load_runner_module`, `_mk`, `_run_state`,
`_observed`, and `_stub_loop`, then migrated
`test_reject_impl_feedback.py`, `test_reject_test_routing.py`, and
`test_spec_blocked_signal.py` to import them. The drift (one file tracked
`td_phase_steps`, the others did not) is collapsed: `_observed` now always
carries `td_phase_steps` and `_stub_loop` always records it. Per-file stub
differences (SPEC_OR_TEST_BLOCKED executor, verify-green must fail, no
evidence bundle, stubbed validators, stubbed executor-prompt rendering) are
expressed as explicit keyword flags. Run identity was consolidated to a
generic `r-test` (no migrated test asserts `run_id`/`run_label`).

### 4. Tool lists from `DEFAULT_ENABLED_TOOLS`

`executor.md` advertised the invalid ids `Write`/`MultiEdit` and
`test-designer.md` advertised `Write`. Both now render
`{{enabled_tools}}`, populated by `render_executor_prompt` /
`render_test_designer_prompt` from
`DEFAULT_ENABLED_TOOLS[Role.EXECUTOR]` /
`DEFAULT_ENABLED_TOOLS[Role.TEST_DESIGNER]`. Updated the
`test_prompt_templates_render_against_minimal_context` fixture to supply
`enabled_tools`. `validator.md` was left unchanged: its hand-written
`Read,Glob,Grep,LS` (no `Execute`) is correct and deliberately reflects
bundle-mode, which differs from `DEFAULT_ENABLED_TOOLS[VALIDATOR]`.

### 5. `PLAN_HASH` footer

Changed the planner footer from "The runner replaces the placeholder
before hashing" to state that the runner hashes the final message
verbatim (including the literal `PLAN_HASH:` line) and stores the hash
separately; no substitution occurs.

---

## Tests

```
473 passed, 3 skipped, 1 failed
```

The 1 failure is the known environmental test
`tests/test_sign_chunk_token.py::test_replay_chunk13_succeeds`
(chunk-13 fixture subject matches 2 commits in this checkout), pre-existing
to this branch. Full suite was run and verified green after every commit.

---

## Deferrals / notes

- Pre-existing ruff lint debt in `tools/sprint_loop/per_chunk.py` (import
  order) and `tests/test_sprint_loop.py` was not touched; the gate for this
  PR is pytest, and those violations predate the branch.
- Out of scope: `sprint-loop.py::_main_inner` still hardcodes per-role
  `enabled_tools` strings (planner/test-designer/executor) that drift from
  `DEFAULT_ENABLED_TOOLS`. Item 4 only made the prompt templates render the
  canonical lists; the invocation-side allowlists were left as-is per the
  five-item scope.

"""Shared test helpers for the per-chunk routing / signal suites.

``test_reject_impl_feedback.py``, ``test_reject_test_routing.py`` and
``test_spec_blocked_signal.py`` each pasted their own copy of the
runner-loader / run-state / stub-loop block. Those copies drifted — one
tracked ``td_phase_steps`` while the others did not. These are the single
source of truth.

The helpers are plain functions rather than pytest fixtures on purpose:
they take per-file parameters (loader name, run identity, stub shape)
that a fixture cannot express as cleanly, and the three files already
call them directly.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from typing import Any

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TOOLS = os.path.join(_REPO, "tools")
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)

from sprint_loop.state import Role, RoleAssignment, RunState  # noqa: E402


def _load_runner_module(name: str = "sprint_loop_runner") -> Any:
    """Load ``tools/sprint-loop.py`` as a module without running ``main()``."""
    runner_path = os.path.join(_REPO, "tools", "sprint-loop.py")
    spec = importlib.util.spec_from_file_location(name, runner_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _mk(role: Role, model: str, family: str, provider: str = "x") -> RoleAssignment:
    return RoleAssignment(
        role=role, pinned_model_id=model, pinned_family=family, pinned_provider=provider
    )


def _run_state(pilot_root: str, framework_root: str = "/tmp/fw") -> RunState:
    """A minimally-populated RunState with all five seats pinned.

    The run identity values are cosmetic here (no test asserts ``run_id`` /
    ``run_label``); what matters is the populated seat assignments so the
    runner's family-guard and role-attribution paths behave.
    """
    rs = RunState(
        run_id="r-test",
        started_at="2026-01-01T00:00:00Z",
        framework_root=framework_root,
        pilot_root=pilot_root,
        pilot_python="/usr/bin/true",
        run_label="r-test",
    )
    rs.planner = _mk(Role.PLANNER, "claude-opus-5", "claude-family")
    rs.plan_reviewer = _mk(Role.PLAN_REVIEWER, "grok-4.5", "grok-family")
    rs.test_designer = _mk(Role.TEST_DESIGNER, "claude-opus-5", "claude-family")
    rs.executor = _mk(Role.EXECUTOR, "gpt-5.4-mini", "openai-family")
    rs.validators = [
        _mk(Role.VALIDATOR, "grok-4.5", "grok-family"),
        _mk(Role.VALIDATOR, "gemini-3.1-pro-preview", "gemini-family"),
    ]
    return rs


def _observed() -> dict[str, Any]:
    """The shared per-test observation counters (superset across the suites)."""
    return {
        "lock_test": 0,
        "invoke_test_designer": 0,
        "invoke_executor": 0,
        "verify_green": 0,
        "produce_evidence": 0,
        "run_validators": 0,
        "td_phase_steps": [],
    }


def _stub_loop(
    mod: Any,
    monkeypatch: Any,
    chunk: Any,
    tmp_path: Any,
    observed: dict[str, Any],
    *,
    regenerated_test_is_green: bool = True,
    executor_result: str = "executor ok",
    verify_green_fails: bool = False,
    produce_bundle: bool = True,
    stub_run_validators: bool = False,
    stub_render_executor_prompt: bool = False,
) -> None:
    """Stub every seat + subprocess step so the tests exercise routing only.

    The common shape serves the REJECT_IMPLEMENTATION / REJECT_TEST
    routing suites. ``test_spec_blocked_signal.py`` flips the flags that
    make the executor report ``SPEC_OR_TEST_BLOCKED`` and then assert that
    verify-green / evidence / validators never run.
    """
    test_abs = os.path.join(str(tmp_path / "pilot"), chunk.locked_test_files[0])

    def fake_lock_test(*a, **k):
        observed["lock_test"] += 1
        chunk.lock_manifest_path = str(tmp_path / "lock.json")
        chunk.locked_test_sha = "lock-sha"
        return {"sha256": "lock-sha"}

    def fake_invoke_test_designer(*a, **k):
        observed["invoke_test_designer"] += 1
        observed["td_phase_steps"].append(k.get("phase_step"))
        os.makedirs(os.path.dirname(test_abs), exist_ok=True)
        with open(test_abs, "w") as f:
            f.write("def test_devices():\n    assert False\n")
        return {"result_text": "STATUS: TEST_AUTHORED"}

    def fake_invoke_executor(*a, **k):
        observed["invoke_executor"] += 1
        return {"result_text": executor_result}

    def fake_validate_red(*a, **k):
        if regenerated_test_is_green and observed["invoke_test_designer"] >= 1:
            raise RuntimeError("test is not RED — it already passes")
        return {"valid": True}

    monkeypatch.setattr(mod, "lock_test", fake_lock_test)
    monkeypatch.setattr(mod, "validate_red", fake_validate_red)
    monkeypatch.setattr(mod, "invoke_test_designer", fake_invoke_test_designer)
    monkeypatch.setattr(mod, "invoke_executor", fake_invoke_executor)

    if verify_green_fails:
        def fail_verify_green(*a, **k):
            observed["verify_green"] += 1
            raise AssertionError("verify_green should not be called")
        monkeypatch.setattr(mod, "verify_green", fail_verify_green)
    else:
        monkeypatch.setattr(mod, "verify_green", lambda *a, **k: {"green": True})

    if produce_bundle:
        def fake_produce_evidence(*a, **k):
            chunk.evidence_bundle_path = str(tmp_path / "bundle.json")
            return {}
        monkeypatch.setattr(mod, "produce_evidence", fake_produce_evidence)
    else:
        def fake_produce_evidence_no_bundle(*a, **k):
            observed["produce_evidence"] += 1
            return {}
        monkeypatch.setattr(mod, "produce_evidence", fake_produce_evidence_no_bundle)

    if stub_run_validators:
        def fake_run_validators(*a, **k):
            observed["run_validators"] += 1
            return None
        monkeypatch.setattr(mod, "run_validators", fake_run_validators)

    if stub_render_executor_prompt:
        monkeypatch.setattr(mod, "render_executor_prompt", lambda *a, **k: "")

    monkeypatch.setattr(mod, "recheck_family_guard_post_resolution", lambda *a, **k: None)

"""Tests for the test_designer auto-fire path in ``run_chunk_inner``.

A chunk spec names its locked test file. If that file does not exist
on disk yet, the runner must fire the test_designer droid role to
author it before locking — otherwise ``lock.py`` runs against a
missing path. These tests pin that branch, its skip conditions, and
the context the designer prompt carries.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys

_TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)

import pytest  # noqa: E402
from sprint_loop.config import Config  # noqa: E402
from sprint_loop.per_chunk import (  # noqa: E402
    _format_chunk_spec,
    render_test_designer_prompt,
)
from sprint_loop.state import (  # noqa: E402
    ChunkState,
    GateDecision,
    Role,
    RoleAssignment,
    RunState,
)


def _load_runner_module():
    """Load sprint-loop.py as a module without running main()."""
    repo = (
        subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], cwd=os.path.dirname(_TOOLS)
        )
        .decode()
        .strip()
    )
    runner_path = os.path.join(repo, "tools", "sprint-loop.py")
    spec = importlib.util.spec_from_file_location("sprint_loop_runner_td", runner_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _mk(role: Role, model: str, family: str, provider: str = "x") -> RoleAssignment:
    return RoleAssignment(
        role=role, pinned_model_id=model, pinned_family=family, pinned_provider=provider
    )


def _run_state(pilot_root: str) -> RunState:
    rs = RunState(
        run_id="r-td-test",
        started_at="2026-08-16T00:00:00Z",
        framework_root="/tmp/fw",
        pilot_root=pilot_root,
        pilot_python="/usr/bin/true",
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


def _chunk(test_files: list[str]) -> ChunkState:
    return ChunkState(
        chunk_id="c-td",
        scope="auto-fire the test designer",
        observable_criteria=["the designer is invoked when the test is absent"],
        locked_test_files=test_files,
        commands=["/usr/bin/true -m pytest test/test_autofire.py -v"],
        accepted_assertion="autofire assertion phrase",
    )


def _stub_downstream(mod, monkeypatch, chunk, tmp_path, observed):
    """No-op every step after lock so the tests exercise step 1 only."""

    def fake_lock_test(*args, **kwargs):
        observed["lock_test"] += 1
        chunk.lock_manifest_path = str(tmp_path / "lock.json")
        chunk.locked_test_sha = "lock-sha"
        return {"sha256": "lock-sha"}

    def fake_produce_evidence(*args, **kwargs):
        chunk.evidence_bundle_path = str(tmp_path / "bundle.json")
        return None

    def fake_run_validators(*args, **kwargs):
        return type(
            "BackendResultStub",
            (),
            {
                "gate": GateDecision.ACCEPT,
                "reason": "ok",
                "findings": [],
                # The runner classifies the rejection from the panel's
                # per-validator verdicts, so the stub must carry the list.
                "validators": [],
            },
        )()

    monkeypatch.setattr(mod, "lock_test", fake_lock_test)
    monkeypatch.setattr(mod, "validate_red", lambda *a, **k: None)
    monkeypatch.setattr(mod, "invoke_executor", lambda *a, **k: {"result_text": "ok"})
    monkeypatch.setattr(mod, "render_executor_prompt", lambda *a, **k: "")
    monkeypatch.setattr(mod, "verify_green", lambda *a, **k: None)
    monkeypatch.setattr(mod, "produce_evidence", fake_produce_evidence)
    monkeypatch.setattr(mod, "run_validators", fake_run_validators)
    monkeypatch.setattr(mod, "recheck_family_guard_post_resolution", lambda *a, **k: None)


def test_empty_locked_test_files_still_raises(tmp_path):
    mod = _load_runner_module()
    rs = _run_state(str(tmp_path))
    chunk = _chunk([])
    with pytest.raises(RuntimeError) as exc:
        mod.run_chunk_inner(rs, chunk, str(tmp_path), False, Config())
    assert "no locked_test_files" in str(exc.value)


def test_missing_test_file_fires_test_designer_then_locks(tmp_path, monkeypatch):
    mod = _load_runner_module()
    pilot = tmp_path / "pilot"
    (pilot / "test").mkdir(parents=True)
    rs = _run_state(str(pilot))
    chunk = _chunk(["test/test_autofire.py"])
    observed = {"invoke_test_designer": 0, "lock_test": 0}

    def fake_invoke_test_designer(*args, **kwargs):
        observed["invoke_test_designer"] += 1
        (pilot / "test" / "test_autofire.py").write_text(
            "def test_x():\n    assert False, 'autofire assertion phrase'\n"
        )
        return {"result_text": "STATUS: TEST_AUTHORED"}

    _stub_downstream(mod, monkeypatch, chunk, tmp_path, observed)
    monkeypatch.setattr(mod, "invoke_test_designer", fake_invoke_test_designer)

    mod.run_chunk_inner(rs, chunk, str(tmp_path / "ev"), False, Config())

    assert observed["invoke_test_designer"] == 1
    assert observed["lock_test"] == 1
    assert os.path.isfile(str(tmp_path / "ev" / "c-td-td-prompt.md"))


def test_existing_test_file_does_not_fire_test_designer(tmp_path, monkeypatch):
    mod = _load_runner_module()
    pilot = tmp_path / "pilot"
    (pilot / "test").mkdir(parents=True)
    (pilot / "test" / "test_autofire.py").write_text(
        "def test_x():\n    assert False, 'autofire assertion phrase'\n"
    )
    rs = _run_state(str(pilot))
    chunk = _chunk(["test/test_autofire.py"])
    observed = {"invoke_test_designer": 0, "lock_test": 0}

    def fake_invoke_test_designer(*args, **kwargs):
        observed["invoke_test_designer"] += 1
        return {"result_text": ""}

    _stub_downstream(mod, monkeypatch, chunk, tmp_path, observed)
    monkeypatch.setattr(mod, "invoke_test_designer", fake_invoke_test_designer)

    mod.run_chunk_inner(rs, chunk, str(tmp_path / "ev"), False, Config())

    assert observed["invoke_test_designer"] == 0
    assert observed["lock_test"] == 1


def test_test_designer_writing_nothing_raises(tmp_path, monkeypatch):
    mod = _load_runner_module()
    pilot = tmp_path / "pilot"
    (pilot / "test").mkdir(parents=True)
    rs = _run_state(str(pilot))
    chunk = _chunk(["test/test_autofire.py"])
    observed = {"invoke_test_designer": 0, "lock_test": 0}

    _stub_downstream(mod, monkeypatch, chunk, tmp_path, observed)
    monkeypatch.setattr(mod, "invoke_test_designer", lambda *a, **k: {"result_text": ""})

    with pytest.raises(RuntimeError) as exc:
        mod.run_chunk_inner(rs, chunk, str(tmp_path / "ev"), False, Config())
    msg = str(exc.value)
    assert "c-td" in msg
    assert str(pilot / "test" / "test_autofire.py") in msg
    assert "c-td-td-envelope.json" in msg
    assert "stderr-test-designer.log" in msg
    assert observed["lock_test"] == 0


def test_format_chunk_spec_emits_accepted_assertion_only_when_set():
    chunk = _chunk(["test/test_autofire.py"])
    spec = _format_chunk_spec(chunk)
    assert "ACCEPTED_ASSERTION: autofire assertion phrase" in spec

    chunk.accepted_assertion = ""
    assert "ACCEPTED_ASSERTION" not in _format_chunk_spec(chunk)


def test_test_designer_prompt_carries_assertion_and_sibling_dir(tmp_path):
    rs = _run_state(str(tmp_path / "pilot"))
    chunk = _chunk(["test/test_autofire.py"])
    out = tmp_path / "td-prompt.md"
    render_test_designer_prompt(chunk, rs, "the pilot spec body", str(out))
    text = out.read_text()

    assert "autofire assertion phrase" in text
    assert str(tmp_path / "pilot" / "test") in text
    assert "-m pytest test/test_autofire.py -v" in text
    assert "the pilot spec body" in text
    assert "{{" not in text

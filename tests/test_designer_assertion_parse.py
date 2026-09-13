"""Regression test for ACCEPTED_ASSERTION parse (finding P2-d).

test-designer.md promises the runner parses the designer's
ACCEPTED_ASSERTION line and passes it as --accepted-assertion. Before
this fix, no such parse existed — the pipeline only used
chunk.accepted_assertion as pre-filled by _chunks_from_file. Now
per_chunk.parse_accepted_assertion extracts the phrase and
run_chunk_inner threads it into chunk.accepted_assertion.
"""

from __future__ import annotations

import importlib.util
import os
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TOOLS = os.path.join(_REPO, "tools")
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)

import pytest  # noqa: E402
from sprint_loop.per_chunk import parse_accepted_assertion  # noqa: E402
from sprint_loop.state import (  # noqa: E402
    ChunkState,
    GateDecision,
    Role,
    RoleAssignment,
    RunState,
)
from sprint_loop.config import Config  # noqa: E402


def _load_runner():
    runner_path = os.path.join(_TOOLS, "sprint-loop.py")
    spec = importlib.util.spec_from_file_location("sprint_loop_runner_td_parse", runner_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── parse_accepted_assertion unit tests ──────────────────────────────────


def test_parse_extracts_assertion_from_result_text():
    text = (
        "STATUS: TEST_AUTHORED\n"
        "TEST_FILE: tests/test_new.py\n"
        "ACCEPTED_ASSERTION: the new route returns 200\n"
    )
    assert parse_accepted_assertion(text) == "the new route returns 200"


def test_parse_returns_none_when_line_is_absent():
    text = "STATUS: TEST_AUTHORED\nTEST_FILE: tests/test_new.py\n"
    assert parse_accepted_assertion(text) is None


def test_parse_strips_whitespace():
    text = "ACCEPTED_ASSERTION:   spaced phrase   \n"
    assert parse_accepted_assertion(text) == "spaced phrase"


def test_parse_takes_first_occurrence():
    text = (
        "ACCEPTED_ASSERTION: first phrase\n"
        "ACCEPTED_ASSERTION: second phrase\n"
    )
    assert parse_accepted_assertion(text) == "first phrase"


def test_parse_handles_empty_string():
    assert parse_accepted_assertion("") is None


def test_parse_handles_inline_text():
    # The line must start with ACCEPTED_ASSERTION: at the beginning of
    # a line. Text like "some ACCEPTED_ASSERTION: foo" should not match.
    text = "here is ACCEPTED_ASSERTION: inline\n"
    assert parse_accepted_assertion(text) is None


# ── Integration: run_chunk_inner threads parsed assertion ────────────────


def _mk(role: Role, model: str, family: str) -> RoleAssignment:
    return RoleAssignment(role=role, pinned_model_id=model, pinned_family=family)


def _run_state(pilot_root: str) -> RunState:
    rs = RunState(
        run_id="r-td-parse",
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


def _stub_all(mod, monkeypatch, chunk, tmp_path, td_result_text):
    """Stub all steps; the test-designer returns ``td_result_text``."""
    observed = {"assertion_at_lock": None}

    def fake_invoke_td(*args, **kwargs):
        # Write the test file (the designer produces it)
        pilot_root = args[1].pilot_root if len(args) > 1 else kwargs.get("rs", args[0]).pilot_root
        test_path = os.path.join(
            pilot_root, chunk.locked_test_files[0]
        )
        os.makedirs(os.path.dirname(test_path), exist_ok=True)
        with open(test_path, "w") as f:
            f.write("def test_x():\n    assert False, 'parsed assertion phrase'\n")
        return {"result_text": td_result_text}

    def fake_lock_test(c, **kwargs):
        observed["assertion_at_lock"] = kwargs.get("accepted_assertion", "")
        c.lock_manifest_path = str(tmp_path / "lock.json")
        c.locked_test_sha = "lock-sha"
        return {"sha256": "lock-sha"}

    def fake_produce_evidence(*a, **k):
        chunk.evidence_bundle_path = str(tmp_path / "bundle.json")

    def fake_validators(*a, **k):
        return type("R", (), {"gate": GateDecision.ACCEPT, "reason": "ok", "findings": []})()

    monkeypatch.setattr(mod, "invoke_test_designer", fake_invoke_td)
    monkeypatch.setattr(mod, "lock_test", fake_lock_test)
    monkeypatch.setattr(mod, "validate_red", lambda *a, **k: None)
    monkeypatch.setattr(mod, "invoke_executor", lambda *a, **k: {"result_text": "ok"})
    monkeypatch.setattr(mod, "render_executor_prompt", lambda *a, **k: "")
    monkeypatch.setattr(mod, "verify_green", lambda *a, **k: None)
    monkeypatch.setattr(mod, "produce_evidence", fake_produce_evidence)
    monkeypatch.setattr(mod, "run_validators", fake_validators)
    monkeypatch.setattr(mod, "recheck_family_guard_post_resolution", lambda *a, **k: None)

    return observed


def test_designer_assertion_overrides_chunk_preset(tmp_path, monkeypatch):
    """When the designer emits ACCEPTED_ASSERTION, it overrides whatever
    the chunk spec pre-populated."""
    mod = _load_runner()
    pilot = tmp_path / "pilot"
    (pilot / "test").mkdir(parents=True)
    rs = _run_state(str(pilot))

    chunk = ChunkState(
        chunk_id="c-td-parse",
        scope="parse assertion test",
        observable_criteria=["parse works"],
        locked_test_files=["test/test_parse.py"],
        commands=["/usr/bin/true"],
        accepted_assertion="old-from-chunks-file",
    )

    td_text = "STATUS: TEST_AUTHORED\nACCEPTED_ASSERTION: parsed assertion phrase\n"
    observed = _stub_all(mod, monkeypatch, chunk, tmp_path, td_text)

    mod.run_chunk_inner(rs, chunk, str(tmp_path / "ev"), False, Config())

    # The parsed assertion must have overridden the chunks_file default
    assert chunk.accepted_assertion == "parsed assertion phrase"
    assert observed["assertion_at_lock"] == "parsed assertion phrase"


def test_designer_missing_assertion_keeps_chunk_preset(tmp_path, monkeypatch):
    """When the designer does NOT emit ACCEPTED_ASSERTION, the pre-set
    value from chunks_file is used."""
    mod = _load_runner()
    pilot = tmp_path / "pilot"
    (pilot / "test").mkdir(parents=True)
    rs = _run_state(str(pilot))

    chunk = ChunkState(
        chunk_id="c-td-parse",
        scope="fallback assertion test",
        observable_criteria=["fallback works"],
        locked_test_files=["test/test_parse.py"],
        commands=["/usr/bin/true"],
        accepted_assertion="preset-from-chunks",
    )

    td_text = "STATUS: TEST_AUTHORED\n"  # no ACCEPTED_ASSERTION line
    observed = _stub_all(mod, monkeypatch, chunk, tmp_path, td_text)

    mod.run_chunk_inner(rs, chunk, str(tmp_path / "ev"), False, Config())

    # Falls back to the chunk spec's value
    assert chunk.accepted_assertion == "preset-from-chunks"
    assert observed["assertion_at_lock"] == "preset-from-chunks"

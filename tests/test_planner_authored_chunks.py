"""Tests for the authored chunk contract reaching the planner prompt.

Execution is driven by the operator's ``--chunks-file``. A planner that
never sees it invents chunk boundaries, file paths and locked tests that
will never run, and the cross-family plan reviewers then spend their
findings auditing the invention instead of the contract. These tests pin
the contract into the rendered planner prompt.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TOOLS = os.path.join(_REPO, "tools")
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)

from sprint_loop.droid import RunRecord  # noqa: E402
from sprint_loop.state import RunState  # noqa: E402

SENTINEL = "(none supplied — propose a chunking)"


def _load_runner_module():
    """Load sprint-loop.py as a module without running main()."""
    runner_path = os.path.join(_TOOLS, "sprint-loop.py")
    spec = importlib.util.spec_from_file_location("sprint_loop_runner_authored", runner_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _two_chunk_fixture() -> list[dict]:
    return [
        {
            "chunk_id": "c1",
            "scope": "Add the public route",
            "observable_criteria": [
                "GET /llms.txt returns 200",
                "Content-Type starts with text/plain",
            ],
            "allowed_files": ["app.py", "api/llms_txt.py"],
            "locked_test_files": ["test/test_public_routes.py"],
            "commands": ["python -m pytest test/test_public_routes.py -v"],
            "red_command": "python -m pytest test/test_public_routes.py -v",
            "green_command": "python -m pytest test/test_public_routes.py -v",
            "full_suite_command": "python -m pytest -v",
            "lint_command": "ruff check .",
            "build_command": "python -m compileall app.py",
        },
        {
            "chunk_id": "c2",
            "scope": "Link the route from the footer",
            "criteria": ["Footer renders a link to /llms.txt"],
            "allowed_files": ["templates/base.html"],
            "locked_test_files": ["test/test_footer.py"],
            "commands": ["python -m pytest test/test_footer.py -v"],
        },
    ]


def _write_chunks(tmp_path, payload) -> str:
    path = tmp_path / "chunks.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))
    return str(path)


def test_format_renders_criteria_files_tests_and_commands(tmp_path):
    mod = _load_runner_module()
    path = _write_chunks(tmp_path, {"chunks": _two_chunk_fixture()})
    out = mod._format_authored_chunks(path)

    assert "c1" in out
    assert "c2" in out
    assert "test/test_public_routes.py" in out
    assert "test/test_footer.py" in out
    assert "api/llms_txt.py" in out
    assert "GET /llms.txt returns 200" in out
    assert "Footer renders a link to /llms.txt" in out
    assert "ruff check ." in out
    assert "python -m pytest -v" in out
    assert "python -m compileall app.py" in out
    # Markdown, not a JSON blob.
    assert "### c1" in out
    assert '"chunk_id"' not in out


def test_format_accepts_bare_list_shape(tmp_path):
    mod = _load_runner_module()
    path = _write_chunks(tmp_path, _two_chunk_fixture())
    out = mod._format_authored_chunks(path)
    assert "### c1" in out
    assert "### c2" in out
    assert "GET /llms.txt returns 200" in out


def test_format_accepts_both_criteria_key_spellings(tmp_path):
    mod = _load_runner_module()
    observable = _write_chunks(tmp_path / "a", {"chunks": [_two_chunk_fixture()[0]]})
    plain = _write_chunks(tmp_path / "b", {"chunks": [_two_chunk_fixture()[1]]})
    assert "GET /llms.txt returns 200" in mod._format_authored_chunks(observable)
    assert "Footer renders a link to /llms.txt" in mod._format_authored_chunks(plain)


def test_format_returns_sentinel_for_missing_path(tmp_path):
    mod = _load_runner_module()
    assert mod._format_authored_chunks(None) == SENTINEL
    assert mod._format_authored_chunks("") == SENTINEL
    assert mod._format_authored_chunks(str(tmp_path / "nope.json")) == SENTINEL


def test_format_returns_sentinel_for_malformed_json(tmp_path):
    mod = _load_runner_module()
    path = tmp_path / "broken.json"
    path.write_text("{not json at all,,,")
    assert mod._format_authored_chunks(str(path)) == SENTINEL


def test_format_returns_sentinel_for_empty_chunk_list(tmp_path):
    mod = _load_runner_module()
    assert mod._format_authored_chunks(_write_chunks(tmp_path, {"chunks": []})) == SENTINEL


def _render_plan_prompt(mod, monkeypatch, tmp_path, *, chunks_file: str) -> str:
    """Run the planner with a stubbed droid call; return plan-prompt.md."""
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir(exist_ok=True)
    stderr_path = evidence_dir / "planner-stderr.log"
    stderr_path.write_text("")

    plan = "# Sprint plan\n\n" + "\n\n".join(
        f"## {name}\n\n" + (f"Body for {name}. " * 20)
        for name in (
            "Sprint Metadata",
            "Objectives",
            "Current state / root cause",
            "Risk assessment",
            "Acceptance criteria",
            "Test strategy",
            "Chunk plan",
            "Open questions",
        )
    )

    def fake_invoke(role, **kwargs):
        with open(kwargs["envelope_path"], "w") as f:
            json.dump({"result": plan, "is_error": False}, f)
        return RunRecord(
            run_id="r-authored",
            role="planner",
            model_id="claude-opus-5",
            provider="anthropic",
            family="claude-family",
            provider_lock="anthropic",
            api_provider_lock="anthropic",
            envelope_path=kwargs["envelope_path"],
            stderr_path=str(stderr_path),
        )

    monkeypatch.setattr(mod, "invoke_droid", fake_invoke)
    monkeypatch.setattr(mod, "append_run_record", lambda record, **kwargs: None)

    rs = RunState(
        run_id="r-authored",
        started_at="2026-01-01T00:00:00Z",
        framework_root=_REPO,
        pilot_root=str(tmp_path),
        pilot_python=sys.executable,
        chunks_file=chunks_file,
    )
    mod.run_planner(
        rs,
        pilot_spec_text="the pilot exposes a public route",
        evidence_dir=str(evidence_dir),
        dry_run=False,
    )
    return (evidence_dir / "plan-prompt.md").read_text()


def test_rendered_prompt_contains_the_authored_contract(tmp_path, monkeypatch):
    mod = _load_runner_module()
    chunks_file = _write_chunks(tmp_path, {"chunks": _two_chunk_fixture()})
    text = _render_plan_prompt(mod, monkeypatch, tmp_path, chunks_file=chunks_file)

    assert "{{authored_chunks}}" not in text
    assert "### c1" in text
    assert "### c2" in text
    assert "test/test_public_routes.py" in text
    assert "GET /llms.txt returns 200" in text
    assert SENTINEL not in text


def test_rendered_prompt_contains_the_sentinel_without_a_chunks_file(tmp_path, monkeypatch):
    mod = _load_runner_module()
    text = _render_plan_prompt(mod, monkeypatch, tmp_path, chunks_file="")
    assert "{{authored_chunks}}" not in text
    assert SENTINEL in text

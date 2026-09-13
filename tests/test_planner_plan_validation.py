"""Tests for the planner plan-document contract.

The planner seat is read-only (no file-writing tool), so its envelope
``result`` is the plan. A seat that believes it must write a file can
fail that write and still close with "the document has been saved" — at
which point the runner used to hash the chat summary as the plan and
spend two cross-family review calls rejecting it. These tests pin the
structural check that stops that shape at the source.
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

import pytest  # noqa: E402
from sprint_loop.droid import RunRecord  # noqa: E402
from sprint_loop.state import RunState  # noqa: E402


def _load_runner_module():
    """Load sprint-loop.py as a module without running main()."""
    runner_path = os.path.join(_TOOLS, "sprint-loop.py")
    spec = importlib.util.spec_from_file_location("sprint_loop_runner_plan_val", runner_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# The literal final message observed on the failing run: the planner's
# base64 write one-liner died with a SyntaxError and the seat reported
# success anyway.
OBSERVED_STUB = (
    "The planning document for the adversarial sprint has been "
    "successfully generated and saved to the required location.\n\n"
    "Output Artifact:\n`plan.md`\n"
)

_SECTION_HEADINGS = (
    "## Sprint Metadata",
    "## Objectives",
    "## Current state / root cause / opportunity",
    "## Risk assessment",
    "## Acceptance criteria",
    "## Test strategy",
    "## Chunk plan",
    "## Open questions",
)


def _valid_plan(*, drop: str | None = None) -> str:
    """Synthesize a plan with all eight sections and enough body."""
    parts = ["# Sprint plan\n"]
    for heading in _SECTION_HEADINGS:
        if drop is not None and drop.lower() in heading.lower():
            continue
        body = f"Body text for {heading.lstrip('# ')}. " * 20
        parts.append(f"{heading}\n\n{body}\n")
    parts.append("PLAN_HASH: <computed-by-runner>\n")
    return "\n".join(parts)


def test_valid_plan_has_no_problems():
    mod = _load_runner_module()
    plan = _valid_plan()
    assert len(plan) >= mod._PLAN_MIN_CHARS
    assert mod._validate_plan_document(plan) == []


def test_tolerant_heading_forms_still_match():
    """Bold and numbered headings count — the planner will not reproduce
    our exact punctuation."""
    mod = _load_runner_module()
    plan = _valid_plan()
    plan = plan.replace("## Sprint Metadata", "**Sprint Metadata**")
    plan = plan.replace("## Objectives", "2. Objectives")
    plan = plan.replace(
        "## Current state / root cause / opportunity", "3. CURRENT STATE / root cause"
    )
    assert mod._validate_plan_document(plan) == []


def test_missing_section_is_reported_by_name():
    mod = _load_runner_module()
    problems = mod._validate_plan_document(_valid_plan(drop="Test strategy"))
    assert problems, "a plan missing a required section must be rejected"
    assert any("Test strategy" in p for p in problems)


def test_observed_stub_reads_as_a_report_about_a_plan():
    mod = _load_runner_module()
    problems = mod._validate_plan_document(OBSERVED_STUB)
    assert any("reads as a report about a plan rather than a plan" in p for p in problems)
    assert any("missing required section" in p for p in problems)


def test_short_document_is_reported():
    mod = _load_runner_module()
    problems = mod._validate_plan_document("# Sprint plan\n\n## Objectives\n- do a thing\n")
    assert any("too short" in p for p in problems)


def _fake_planner_record(envelope_path: str, stderr_path: str, result: str) -> RunRecord:
    with open(envelope_path, "w") as f:
        json.dump({"result": result, "is_error": False}, f)
    return RunRecord(
        run_id="r-plan-val",
        role="planner",
        model_id="claude-opus-5",
        provider="anthropic",
        family="claude-family",
        provider_lock="anthropic",
        api_provider_lock="anthropic",
        envelope_path=envelope_path,
        stderr_path=stderr_path,
    )


def _run_planner_with_result(mod, monkeypatch, tmp_path, result: str):
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    stderr_path = evidence_dir / "planner-stderr.log"
    stderr_path.write_text("")

    def fake_invoke(role, **kwargs):
        return _fake_planner_record(kwargs["envelope_path"], str(stderr_path), result)

    monkeypatch.setattr(mod, "invoke_droid", fake_invoke)
    monkeypatch.setattr(mod, "append_run_record", lambda record, **kwargs: None)

    rs = RunState(
        run_id="r-plan-val",
        started_at="2026-01-01T00:00:00Z",
        framework_root=_REPO,
        pilot_root=str(tmp_path),
        pilot_python=sys.executable,
    )
    return rs, mod.run_planner(
        rs,
        pilot_spec_text="the pilot exposes a public route",
        evidence_dir=str(evidence_dir),
        dry_run=False,
    )


def test_run_planner_refuses_the_observed_stub(tmp_path, monkeypatch):
    mod = _load_runner_module()
    with pytest.raises(RuntimeError) as exc:
        _run_planner_with_result(mod, monkeypatch, tmp_path, OBSERVED_STUB)
    message = str(exc.value)
    assert "planner-envelope.json" in message
    assert "planner-stderr.log" in message
    assert "plan.md" in message
    assert "may have reported success" in message
    assert "reads as a report about a plan rather than a plan" in message


def test_run_planner_accepts_and_hashes_a_valid_plan(tmp_path, monkeypatch):
    mod = _load_runner_module()
    plan = _valid_plan()
    rs, out = _run_planner_with_result(mod, monkeypatch, tmp_path, plan)
    assert rs.plan_sha256
    assert out["plan_sha256"] == rs.plan_sha256
    assert open(out["plan_doc_path"]).read() == plan

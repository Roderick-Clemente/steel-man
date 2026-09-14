"""Regression test for plan-review loop evidence preservation (finding P2-b).

When the plan-review loop truly iterates (da4b02f), round N must not
overwrite round N-1's artifacts. Each round's plan, prompt, envelope, and
reviewer files are round-indexed so every round survives and
plan_sha256_at_time_of_review remains verifiable against the file it was
computed from.
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
from sprint_loop.state import (  # noqa: E402
    Finding,
    RunState,
    RunStatus,
    hash_text,
)


def _load_runner():
    runner_path = os.path.join(_TOOLS, "sprint-loop.py")
    spec = importlib.util.spec_from_file_location("sprint_loop_runner_evidence", runner_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _valid_plan(tag: str = "") -> str:
    """A structurally valid plan document."""
    sections = [
        ("Sprint Metadata", "Sprint: evidence-test"),
        ("Objectives", "Primary: verify evidence round-indexing"),
        ("Current state / root cause", "Plan evidence was silently overwritten"),
        ("Risk assessment", "Risk: lost audit trail"),
        ("Acceptance criteria", "Round 1 files survive round 2"),
        ("Test strategy", "Unit: this test"),
        ("Chunk plan", "chunk-1: the slice"),
        ("Open questions", "None"),
    ]
    body = "\n\n".join(f"## {name}\n\n{desc} {tag}. " * 20 for name, desc in sections)
    return f"# Sprint plan\n\n{body}\n"


def _fake_record(envelope_path: str, plan_text: str) -> RunRecord:
    os.makedirs(os.path.dirname(envelope_path), exist_ok=True)
    with open(envelope_path, "w") as f:
        json.dump({"result": plan_text, "is_error": False}, f)
    return RunRecord(
        run_id="r-evidence-test",
        role="planner",
        model_id="claude-opus-5",
        provider="anthropic",
        family="claude-family",
        provider_lock="anthropic",
        api_provider_lock="anthropic",
        envelope_path=envelope_path,
        stderr_path="",
    )


def _run_planner_round(mod, monkeypatch, rs, evidence_dir, plan_text):
    """Invoke run_planner with a stub that returns ``plan_text``."""

    def fake_invoke(role, **kwargs):
        return _fake_record(kwargs["envelope_path"], plan_text)

    monkeypatch.setattr(mod, "invoke_droid", fake_invoke)
    monkeypatch.setattr(mod, "append_run_record", lambda record, **kwargs: None)

    mod.run_planner(
        rs,
        pilot_spec_text="(spec)",
        evidence_dir=evidence_dir,
        dry_run=False,
    )


def _run_reviewer_round(mod, monkeypatch, rs, evidence_dir, verdict, findings=None):
    """Invoke run_plan_reviewer with a stub reviewer."""
    review_text = f"VERDICT: {verdict}\n"
    if findings:
        for f in findings:
            review_text += json.dumps({
                "finding_id": f.finding_id,
                "severity": f.severity,
                "category": f.category,
                "claim": f.claim,
                "risk_if_ignored": f.risk_if_ignored,
                "recommended_change": f.recommended_change,
            }) + "\n"

    def fake_invoke(role, **kwargs):
        env_path = kwargs["envelope_path"]
        os.makedirs(os.path.dirname(env_path), exist_ok=True)
        with open(env_path, "w") as f:
            json.dump({"result": review_text, "is_error": False}, f)
        return RunRecord(
            run_id="r-reviewer",
            role="reviewer",
            model_id="grok-4.5",
            provider="xai",
            family="grok-family",
            provider_lock="xai",
            api_provider_lock="xai",
            envelope_path=env_path,
            stderr_path="",
        )

    monkeypatch.setattr(mod, "invoke_droid", fake_invoke)
    monkeypatch.setattr(mod, "append_run_record", lambda record, **kwargs: None)
    monkeypatch.setattr(mod, "_append_finding_rows", lambda findings, **kw: None)

    return mod.run_plan_reviewer(
        rs, reviewer_index=1, evidence_dir=evidence_dir, dry_run=False,
    )


def test_two_review_rounds_preserve_round_one_artifacts(tmp_path, monkeypatch):
    """Run two plan-review rounds and verify round 1 artifacts survive."""
    mod = _load_runner()
    evidence_dir = str(tmp_path / "evidence")
    os.makedirs(evidence_dir, exist_ok=True)

    rs = RunState(
        run_id="r-evidence-test",
        started_at="2026-01-01T00:00:00Z",
        framework_root=_REPO,
        pilot_root=str(tmp_path),
        pilot_python=sys.executable,
    )

    # Round 1
    plan_r1 = _valid_plan("round-one")
    rs.plan_round = 1
    _run_planner_round(mod, monkeypatch, rs, evidence_dir, plan_r1)
    plan_sha256_r1 = rs.plan_sha256
    _run_reviewer_round(mod, monkeypatch, rs, evidence_dir, "REJECT")

    # Verify round 1 files exist
    assert os.path.isfile(os.path.join(evidence_dir, "plan-r1.md"))
    assert os.path.isfile(os.path.join(evidence_dir, "planner-envelope-r1.json"))
    assert os.path.isfile(os.path.join(evidence_dir, "plan-prompt-r1.md"))
    assert os.path.isfile(os.path.join(evidence_dir, "plan-reviewer-1-r1-envelope.json"))

    # Round 2
    plan_r2 = _valid_plan("round-two")
    rs.plan_round = 2
    _run_planner_round(mod, monkeypatch, rs, evidence_dir, plan_r2)
    plan_sha256_r2 = rs.plan_sha256
    _run_reviewer_round(mod, monkeypatch, rs, evidence_dir, "APPROVE")

    # Verify round 2 files exist
    assert os.path.isfile(os.path.join(evidence_dir, "plan-r2.md"))
    assert os.path.isfile(os.path.join(evidence_dir, "planner-envelope-r2.json"))
    assert os.path.isfile(os.path.join(evidence_dir, "plan-prompt-r2.md"))
    assert os.path.isfile(os.path.join(evidence_dir, "plan-reviewer-1-r2-envelope.json"))

    # Round 1 files still exist (not overwritten)
    assert os.path.isfile(os.path.join(evidence_dir, "plan-r1.md"))
    assert os.path.isfile(os.path.join(evidence_dir, "planner-envelope-r1.json"))
    assert os.path.isfile(os.path.join(evidence_dir, "plan-prompt-r1.md"))
    assert os.path.isfile(os.path.join(evidence_dir, "plan-reviewer-1-r1-envelope.json"))

    # Round 1 plan text is intact and its hash is still verifiable
    with open(os.path.join(evidence_dir, "plan-r1.md")) as f:
        assert hash_text(f.read()) == plan_sha256_r1

    # Round 2 plan text is distinct
    with open(os.path.join(evidence_dir, "plan-r2.md")) as f:
        assert hash_text(f.read()) == plan_sha256_r2

    assert plan_sha256_r1 != plan_sha256_r2

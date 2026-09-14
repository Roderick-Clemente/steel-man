"""Timeout handling for the standalone evidence-and-review orchestrator."""

from __future__ import annotations

import importlib.util
import os
import subprocess
from types import SimpleNamespace


_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TOOLS = os.path.join(_REPO, "tools")


def _load_orchestrator():
    path = os.path.join(_TOOLS, "orchestrate-review.py")
    spec = importlib.util.spec_from_file_location("orchestrate_review_timeout", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_step1_fails_closed_with_a_diagnosable_timeout(monkeypatch, capsys):
    orchestrator = _load_orchestrator()
    args = SimpleNamespace(
        pilot_python="/usr/bin/python3",
        framework_root="/framework",
        pilot_root="/pilot",
        test_file="tests/test_widget.py",
        lock_file="locks/test_widget.lock.json",
        evidence_output="/evidence/bundle.json",
        full_suite=True,
        security_scan=True,
        security_allowlist="",
        security_baseline="",
    )

    def timeout(*_args, **_kwargs):
        raise subprocess.TimeoutExpired("local_backend.py", _kwargs["timeout"])

    monkeypatch.setattr(orchestrator.subprocess, "run", timeout)

    result = orchestrator.step1_produce_evidence(args)

    expected_timeout = orchestrator.local_backend_timeout_seconds(
        full_suite=True, security_scan=True
    )
    assert result == {
        "ok": False,
        "error": f"local_backend.py timed out after {expected_timeout}s; evidence was not produced",
    }
    assert result["error"] in capsys.readouterr().err


def test_outer_budget_exceeds_all_enabled_backend_steps():
    orchestrator = _load_orchestrator()
    from sprint_loop.evidence_timeout import (
        BANDIT_TIMEOUT_SECONDS,
        COVERAGE_TIMEOUT_SECONDS,
        GIT_METADATA_TIMEOUT_SECONDS,
        PYTEST_TIMEOUT_SECONDS,
        TOOL_VERSION_TIMEOUT_SECONDS,
        VERIFY_GREEN_TIMEOUT_SECONDS,
    )

    budget = orchestrator.local_backend_timeout_seconds(full_suite=True, security_scan=True)
    inner_steps = (
        VERIFY_GREEN_TIMEOUT_SECONDS
        + PYTEST_TIMEOUT_SECONDS * 2
        + COVERAGE_TIMEOUT_SECONDS
        + BANDIT_TIMEOUT_SECONDS
        + TOOL_VERSION_TIMEOUT_SECONDS * 3
        + GIT_METADATA_TIMEOUT_SECONDS
    )
    assert budget > inner_steps

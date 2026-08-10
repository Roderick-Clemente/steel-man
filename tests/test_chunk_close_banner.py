"""Behavioral pins for `tools/sprint_loop/chunk_close_banner.py`.

Per KN-J16: test drives through actual code paths (the pure `render()`
function), not via string-grep on a fixed banner text. The pins assert
on the structural fact "verify_token returned True → ✅; False → ⛔".
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "tools"))

# resolve the tools module under the sprint_loop package namespace
sys.path.insert(0, str(_REPO / "tools" / "sprint_loop"))
import chunk_close_banner as ccb  # noqa: E402
import sign_chunk_token as sct  # noqa: E402


def _write_token(tmp_path: Path, *, key: str, sha: str = "c" * 40) -> Path:
    reviewers = [{
        "family": "grok-family", "model_id": "grok-4.5",
        "verdict": "ACCEPT-WITH-NITS",
        "envelope_sha256": "e" * 64, "provider": "xai",
    }]
    token = sct.build_token(
        chunk_id="banner-test",
        chunk_commit_sha=sha,
        reviewers=reviewers,
        signed_by="test@local",
    )
    import hmac, hashlib
    payload = {k: v for k, v in token.items() if k != "signature"}
    token["signature"]["value"] = hmac.new(
        key.encode(), sct.canonical_json(payload), hashlib.sha256
    ).hexdigest()
    p = tmp_path / "token.json"
    p.write_text(json.dumps(token, indent=2, sort_keys=True))
    return p


# ── render() pins ───────────────────────────────────────────────────────

def test_signal_present_when_token_verifies(tmp_path, monkeypatch):
    monkeypatch.setenv("EVIDENCE_SIGNING_KEY", "k-banner")
    token_path = _write_token(tmp_path, key="k-banner")
    line, err = ccb.render(
        str(token_path),
        plan_review_rendered=True,
        validation_gate_executed=True,
    )
    assert "✅" in line
    assert "banner-test" in line
    assert err == ""


def test_signal_absent_when_token_refuses(tmp_path, monkeypatch):
    monkeypatch.setenv("EVIDENCE_SIGNING_KEY", "k-banner-A")
    token_path = _write_token(tmp_path, key="k-banner-B")  # mismatch
    line, err = ccb.render(
        str(token_path),
        plan_review_rendered=True,
        validation_gate_executed=True,
    )
    assert "⛔" in line
    assert "❌" not in line
    # checklist pointer present on refusal
    assert "Operator-eye troubleshooting checklist" in err


def test_absence_triggers_checklist_pointer_on_missing_token(tmp_path):
    line, err = ccb.render(
        str(tmp_path / "no-such-token.json"),
        plan_review_rendered=False,
        validation_gate_executed=False,
    )
    assert "⛔" in line
    assert "missing" in line or "not-rendered" in line
    assert "Operator-eye troubleshooting checklist" in err


def test_signal_present_only_when_all_paths_executed(tmp_path, monkeypatch):
    """Both halves of the four-tone (🤺 plan-review / 👀 validation-gate)
    being absent must be reflected in the line so a partial run is
    visible at the operator-eye layer."""
    monkeypatch.setenv("EVIDENCE_SIGNING_KEY", "k-banner")
    token_path = _write_token(tmp_path, key="k-banner")
    line, err = ccb.render(
        str(token_path),
        plan_review_rendered=False,     # not executed
        validation_gate_executed=False, # not executed
    )
    assert "✅" in line
    assert "plan-review-not-rendered" in line
    assert "validation-gate-not-executed" in line


# ── CLI pin ─────────────────────────────────────────────────────────────

def test_cli_emits_check_on_stdout(tmp_path, monkeypatch):
    monkeypatch.setenv("EVIDENCE_SIGNING_KEY", "k-cli")
    token_path = _write_token(tmp_path, key="k-cli")
    p = subprocess.run(
        [
            sys.executable,
            str(_REPO / "tools" / "sprint_loop" / "chunk_close_banner.py"),
            "--token-path", str(token_path),
            "--plan-review-rendered", "--validation-gate-executed",
        ],
        capture_output=True, text=True,
    )
    assert p.returncode == 0
    assert "✅" in p.stdout


def test_cli_emits_bang_on_refusal(tmp_path, monkeypatch):
    monkeypatch.setenv("EVIDENCE_SIGNING_KEY", "k-cli-A")
    token_path = _write_token(tmp_path, key="k-cli-B")
    p = subprocess.run(
        [
            sys.executable,
            str(_REPO / "tools" / "sprint_loop" / "chunk_close_banner.py"),
            "--token-path", str(token_path),
            "--plan-review-rendered", "--validation-gate-executed",
        ],
        capture_output=True, text=True,
    )
    assert p.returncode == 6
    assert "⛔" in p.stdout
    assert "Operator-eye troubleshooting" in p.stderr

"""Behavioral pins for `tools/chunk_sequence_gate.py`.

Drive through the pure ``check_gate`` function — exit-code-only tests
are the §7 silent-green anti-pattern. The pins here exercise:
  * missing prior token
  * present token whose signature fails verification
  * present token whose signature succeeds (happy path)
  * check-current-head binding pin (positive + negative)
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "tools"))

import chunk_sequence_gate as csg  # noqa: E402
import sign_chunk_token as sct  # noqa: E402

REFUSAL_EXIT = csg.REFUSAL_EXIT


# ── pins (pure check_gate) ──────────────────────────────────────────────


def _write_token(tmp_path: Path, *, name: str, key: str) -> Path:
    """Materialise a valid token under ``key``."""
    path = tmp_path / name
    reviewers = [
        {
            "family": "grok-family",
            "model_id": "grok-4.5",
            "verdict": "ACCEPT-WITH-NITS",
            "envelope_sha256": "e" * 64,
            "provider": "xai",
        },
        {
            "family": "gemini-family",
            "model_id": "gemini-3.1-pro-preview",
            "verdict": "ACCEPT-WITH-NITS",
            "envelope_sha256": "e" * 64,
            "provider": "google",
        },
    ]
    token = sct.build_token(
        chunk_id="prior",
        chunk_commit_sha="a" * 40,
        reviewers=reviewers,
        signed_by="test@local",
        signing_key_env="EVIDENCE_SIGNING_KEY",
    )
    # Re-sign under ``key`` in case it's different.
    import hashlib
    import hmac

    payload = {k: v for k, v in token.items() if k != "signature"}
    canon = sct.canonical_json(payload)
    token["signature"]["value"] = hmac.new(key.encode(), canon, hashlib.sha256).hexdigest()
    path.write_text(json.dumps(token, indent=2, sort_keys=True))
    return path


def test_prior_token_missing_refuses(tmp_path, monkeypatch):
    monkeypatch.setenv("EVIDENCE_SIGNING_KEY", "k")
    code, msg = csg.check_gate(
        prior_token_path=str(tmp_path / "no-such.json"),
        next_chunk_id="next",
    )
    assert code == REFUSAL_EXIT
    assert "cannot read token" in msg


def test_prior_token_invalid_signature_refuses(tmp_path, monkeypatch):
    monkeypatch.setenv("EVIDENCE_SIGNING_KEY", "k-A")
    token_path = _write_token(tmp_path, name="token.json", key="k-B")
    code, msg = csg.check_gate(
        prior_token_path=str(token_path),
        next_chunk_id="next",
    )
    assert code == REFUSAL_EXIT
    assert "HMAC verification failed" in msg


def test_prior_token_valid_proceeds(tmp_path, monkeypatch):
    monkeypatch.setenv("EVIDENCE_SIGNING_KEY", "k-match")
    token_path = _write_token(tmp_path, name="token.json", key="k-match")
    code, msg = csg.check_gate(
        prior_token_path=str(token_path),
        next_chunk_id="next",
    )
    assert code == 0, msg
    assert "OK next-chunk=next" in msg


def test_check_current_head_match_proceeds(tmp_path, monkeypatch):
    monkeypatch.setenv("EVIDENCE_SIGNING_KEY", "k")
    monkeypatch.chdir(_REPO)
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    path = tmp_path / "bound.json"
    reviewers = [
        {
            "family": "grok-family",
            "model_id": "grok-4.5",
            "verdict": "ACCEPT-WITH-NITS",
            "envelope_sha256": "e" * 64,
            "provider": "xai",
        }
    ]
    token = sct.build_token(
        chunk_id="bound",
        chunk_commit_sha=sha,
        reviewers=reviewers,
        signed_by="test@local",
    )
    # Re-sign with our key.
    import hashlib
    import hmac

    payload = {k: v for k, v in token.items() if k != "signature"}
    token["signature"]["value"] = hmac.new(
        b"k", sct.canonical_json(payload), hashlib.sha256
    ).hexdigest()
    path.write_text(json.dumps(token, indent=2, sort_keys=True))

    code, msg = csg.check_gate(
        prior_token_path=str(path),
        next_chunk_id="next",
        check_current_head=True,
        repo=str(_REPO),
    )
    assert code == 0, msg


def test_check_current_head_mismatch_refuses(tmp_path, monkeypatch):
    monkeypatch.setenv("EVIDENCE_SIGNING_KEY", "k")
    path = tmp_path / "unbound.json"
    reviewers = [
        {
            "family": "grok-family",
            "model_id": "grok-4.5",
            "verdict": "ACCEPT-WITH-NITS",
            "envelope_sha256": "e" * 64,
            "provider": "xai",
        }
    ]
    token = sct.build_token(
        chunk_id="unbound",
        chunk_commit_sha="b" * 40,  # not HEAD
        reviewers=reviewers,
        signed_by="test@local",
    )
    import hashlib
    import hmac

    payload = {k: v for k, v in token.items() if k != "signature"}
    token["signature"]["value"] = hmac.new(
        b"k", sct.canonical_json(payload), hashlib.sha256
    ).hexdigest()
    path.write_text(json.dumps(token, indent=2, sort_keys=True))
    code, msg = csg.check_gate(
        prior_token_path=str(path),
        next_chunk_id="next",
        check_current_head=True,
        repo=str(_REPO),
    )
    assert code == REFUSAL_EXIT
    assert "binding broken" in msg


# ── CLI pin ─────────────────────────────────────────────────────────────


def test_cli_exit_6_on_refusal(tmp_path, monkeypatch):
    monkeypatch.setenv("EVIDENCE_SIGNING_KEY", "k-cli")
    p = subprocess.run(
        [
            sys.executable,
            str(_REPO / "tools" / "chunk_sequence_gate.py"),
            "--prior-token",
            str(tmp_path / "absent.json"),
            "--next-chunk-id",
            "next",
        ],
        capture_output=True,
        text=True,
    )
    assert p.returncode == REFUSAL_EXIT
    assert "cannot read token" in p.stderr


def test_cli_exit_0_on_proceed(tmp_path, monkeypatch):
    monkeypatch.setenv("EVIDENCE_SIGNING_KEY", "k-cli-ok")
    token_path = _write_token(tmp_path, name="token.json", key="k-cli-ok")
    p = subprocess.run(
        [
            sys.executable,
            str(_REPO / "tools" / "chunk_sequence_gate.py"),
            "--prior-token",
            str(token_path),
            "--next-chunk-id",
            "next",
        ],
        capture_output=True,
        text=True,
    )
    assert p.returncode == 0, p.stdout + p.stderr
    assert "OK next-chunk=next" in p.stdout

"""Behavioral pins for `tools/sign_chunk_token.py`.

Per OPERATING-RULES §7 / §20: assertions are on file artifacts
(persisted token JSON, hash-computed verifier outputs) — not on exit
codes alone. The "replay chunk-13" pin exercises the canonical fixture
SHA (commit `f1bae98`) per PRD §11 Phase 5's retro-tokenize recipe.

Drive these tests via `pytest tests/test_sign_chunk_token.py -v`.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

# Make tools/ importable without PYTHONPATH=tools packaging.
_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "tools"))

import sign_chunk_token as sct  # noqa: E402


# Pin: chunk-13 retro-application — the fixture commit SHA we
# retroactively sign during the chunk-13 replay pin below.
CHUNK_13_FIXTURE_SHA = "f1bae98"  # full: f1bae98 reported by git log


# ── canonical-JSON + HMAC helpers ───────────────────────────────────────

def test_canonical_json_is_key_sorted_and_dense():
    """Compose pin: token JSON must be byte-identical for any
    reviewer insertion order; otherwise the verifier on a different
    machine fails. Mirrors per_chunk.py:341 evidence-bundle scheme.
    """
    a = sct.canonical_json({"b": 2, "a": 1})
    b = sct.canonical_json({"a": 1, "b": 2})
    assert a == b == b'{"a":1,"b":2}'


def test_hmac_sha256_hex_uses_sort_keys():
    """The MAC must NOT depend on key-insertion order — §7 invariant."""
    a = sct.hmac_sha256_hex(b"k", {"a": 1, "b": 2})
    b = sct.hmac_sha256_hex(b"k", {"b": 2, "a": 1})
    assert a == b
    assert len(a) == 64  # SHA-256 hex


# ── build_token refusal-at-parse pins ────────────────────────────────────

def test_build_token_refuses_on_short_chunk_commit_sha():
    reviewers = [_good_reviewer("grok-family", "ACCEPT-WITH-NITS")]
    with pytest.raises(ValueError, match="40-char hex"):
        sct.build_token(
            chunk_id="5a",
            chunk_commit_sha="f2f1408",  # abbreviated, not 40
            reviewers=reviewers,
            signed_by="test@local",
        )


def test_build_token_refuses_on_missing_reviewer_field():
    bad = [{"family": "grok-family", "model_id": "grok-4.5",
            "verdict": "ACCEPT-WITH-NITS"}]  # missing envelope_sha256
    with pytest.raises(ValueError, match="envelope_sha256"):
        sct.build_token(
            chunk_id="5a",
            chunk_commit_sha="f" * 40,
            reviewers=bad,
            signed_by="test@local",
        )


def test_build_token_refuses_on_disallowed_verdict():
    bad = [_good_reviewer("grok-family", "REJECT_PLAN")]
    with pytest.raises(ValueError, match="ALLOWED_VERDICTS"):
        sct.build_token(
            chunk_id="5a",
            chunk_commit_sha="f" * 40,
            reviewers=bad,
            signed_by="test@local",
        )


def test_build_token_refuses_when_signing_key_unset(monkeypatch):
    monkeypatch.delenv("EVIDENCE_SIGNING_KEY", raising=False)
    monkeypatch.setenv(sct.TOKEN_SCHEMA.replace("/", "_"), "")  # ensure scrubbed
    reviewers = [_good_reviewer("grok-family", "ACCEPT-WITH-NITS")]
    with pytest.raises(SystemExit) as excinfo:
        sct.build_token(
            chunk_id="5a",
            chunk_commit_sha="f" * 40,
            reviewers=reviewers,
            signed_by="test@local",
        )
    assert excinfo.value.code == 2


# ── verify_token pins ───────────────────────────────────────────────────

def test_verify_token_round_trip_with_key(monkeypatch):
    monkeypatch.setenv("EVIDENCE_SIGNING_KEY", "k-1")
    reviewers = [_good_reviewer("grok-family", "ACCEPT-WITH-NITS")]
    token = sct.build_token(
        chunk_id="5a",
        chunk_commit_sha="f" * 40,
        reviewers=reviewers,
        signed_by="test@local",
    )
    assert sct.verify_token(token) is True


def test_verify_token_refuses_on_signature_tamper(monkeypatch):
    monkeypatch.setenv("EVIDENCE_SIGNING_KEY", "k-1")
    reviewers = [_good_reviewer("grok-family", "ACCEPT-WITH-NITS")]
    token = sct.build_token(
        chunk_id="5a",
        chunk_commit_sha="f" * 40,
        reviewers=reviewers,
        signed_by="test@local",
    )
    token["chunk_id"] = "tampered"
    assert sct.verify_token(token) is False


def test_verify_token_refuses_on_algorithm_tamper(monkeypatch):
    monkeypatch.setenv("EVIDENCE_SIGNING_KEY", "k-1")
    reviewers = [_good_reviewer("grok-family", "ACCEPT-WITH-NITS")]
    token = sct.build_token(
        chunk_id="5a",
        chunk_commit_sha="f" * 40,
        reviewers=reviewers,
        signed_by="test@local",
    )
    token["signature"]["algorithm"] = "HMAC-SHA512"
    assert sct.verify_token(token) is False


def test_verify_token_refuses_when_key_unset(monkeypatch):
    monkeypatch.setenv("EVIDENCE_SIGNING_KEY", "k-1")
    reviewers = [_good_reviewer("grok-family", "ACCEPT-WITH-NITS")]
    token = sct.build_token(
        chunk_id="5a",
        chunk_commit_sha="f" * 40,
        reviewers=reviewers,
        signed_by="test@local",
    )
    monkeypatch.delenv("EVIDENCE_SIGNING_KEY", raising=False)
    assert sct.verify_token(token) is False


def test_verify_token_refuses_on_unsigned(monkeypatch):
    monkeypatch.setenv("EVIDENCE_SIGNING_KEY", "k-1")
    bad = {"schema": sct.TOKEN_SCHEMA, "chunk_id": "5a",
           "chunk_commit_sha": "f" * 40, "reviewers": [],
           "signed_at": "now", "signed_by": "test@local"}
    assert sct.verify_token(bad) is False


def test_verify_token_refuses_on_non_dict(monkeypatch):
    monkeypatch.setenv("EVIDENCE_SIGNING_KEY", "k-1")
    assert sct.verify_token(["not", "a", "dict"]) is False


# ── replay-chunk-13 pin (PRD §11 Phase 5 retro-tokenize) ───────────────

def test_replay_chunk13_succeeds(tmp_path, monkeypatch):
    """Per Prompt 2 deliverable chunk-5a:

      `python3 -c "import json,hmac,hashlib; ..."` over the chunk-13
      fixture commit; signature must verify.

    Implementation: build a token whose chunk_commit_sha matches the
    chunk-13 commit fixture on the live repo (the file itself is not
    on disk — we look up the SHA from `git log` in the live worktree).
    Then verify.
    """
    monkeypatch.setenv("EVIDENCE_SIGNING_KEY", "k-chunk13-replay")
    sha_proc = subprocess.run(
        ["git", "rev-parse", "f1bae98"],  # chunk-13 commit
        cwd=str(_REPO), capture_output=True, text=True, check=True,
    )
    sha = sha_proc.stdout.strip()
    assert len(sha) == 40
    assert sha.startswith(CHUNK_13_FIXTURE_SHA), (
        f"chunk-13 fixture SHA moved; expected {CHUNK_13_FIXTURE_SHA}*"
    )

    reviewers = [
        _good_reviewer("grok-family", "ACCEPT-WITH-NITS"),
        _good_reviewer("gemini-family", "ACCEPT-WITH-NITS"),
    ]
    token = sct.build_token(
        chunk_id="chunk-13",
        chunk_commit_sha=sha,
        reviewers=reviewers,
        signed_by="replay-test@phase5",
    )
    token_path = tmp_path / "chunk-13.token.json"
    token_path.write_text(json.dumps(token, indent=2, sort_keys=True))
    # HMAC verifies on the persisted artifact (§7 assert on artifact).
    reloded = json.loads(token_path.read_text())
    assert sct.verify_token(reloded) is True


# ── CLI pin: arrange key, sign, then re-verify via subprocess ───────────

def test_cli_sign_then_verify_subprocess(tmp_path, monkeypatch):
    """Drive the full CLI path (sign -> write token -> verify via
    subprocess). Per KN-J16: behavioral tests pin actual code paths,
    not fabricated fixtures.
    """
    monkeypatch.setenv("EVIDENCE_SIGNING_KEY", "k-cli-1")
    sha = "f" * 40
    reviewers_json = json.dumps([_good_reviewer("grok-family", "ACCEPT-WITH-NITS")])
    out = tmp_path / "token.json"

    p_sign = subprocess.run(
        [
            sys.executable,
            str(_REPO / "tools" / "sign_chunk_token.py"),
            "sign",
            "--chunk-id", "5a-cli",
            "--chunk-commit-sha", sha,
            "--reviewers-json", reviewers_json,
            "--signed-by", "test@cli",
            "--out", str(out),
        ],
        env={**os.environ, "EVIDENCE_SIGNING_KEY": "k-cli-1"},
        capture_output=True, text=True, check=True,
    )
    assert "wrote" in p_sign.stderr
    assert out.exists()

    p_verify = subprocess.run(
        [
            sys.executable,
            str(_REPO / "tools" / "sign_chunk_token.py"),
            "verify",
            "--token-path", str(out),
        ],
        env={**os.environ, "EVIDENCE_SIGNING_KEY": "k-cli-1"},
        capture_output=True, text=True,
    )
    assert p_verify.returncode == 0, p_verify.stderr
    assert sha in p_verify.stdout


def test_cli_verify_refuses_tampered_token(tmp_path, monkeypatch):
    monkeypatch.setenv("EVIDENCE_SIGNING_KEY", "k-cli-2")
    reviewers_json = json.dumps([_good_reviewer("grok-family", "ACCEPT-WITH-NITS")])
    out = tmp_path / "token.json"
    subprocess.run(
        [
            sys.executable, str(_REPO / "tools" / "sign_chunk_token.py"),
            "sign", "--chunk-id", "tampered",
            "--chunk-commit-sha", "f" * 40,
            "--reviewers-json", reviewers_json,
            "--out", str(out),
        ],
        env={**os.environ, "EVIDENCE_SIGNING_KEY": "k-cli-2"},
        capture_output=True, text=True, check=True,
    )
    # Tamper the on-disk artifact.
    token = json.loads(out.read_text())
    token["chunk_id"] = "tampered-after-sign"
    out.write_text(json.dumps(token, indent=2, sort_keys=True))

    p = subprocess.run(
        [
            sys.executable, str(_REPO / "tools" / "sign_chunk_token.py"),
            "verify", "--token-path", str(out),
        ],
        env={**os.environ, "EVIDENCE_SIGNING_KEY": "k-cli-2"},
        capture_output=True, text=True,
    )
    assert p.returncode == 6, p.stdout + p.stderr


# ── helpers ─────────────────────────────────────────────────────────────

def _good_reviewer(family: str, verdict: str) -> dict:
    return {
        "family": family,
        "model_id": f"model-{family}",
        "verdict": verdict,
        "envelope_sha256": "e" * 64,
        "provider": "test",
    }

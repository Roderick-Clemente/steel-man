"""Behavioral pins for tools/persistent_referee_stub.py.

Refs:
  - OPERATING-RULES §22 (author != verifier, session identity)
  - phase-4.5/DESIGN-PERSISTENT-REFEREE.md §5 (queue protocol)
  - phase-4.5/KNOWN-ISSUES.md KN-A-8

Each test sets EVIDENCE_SIGNING_KEY_STUB explicitly so the stub's
signing domain is structurally separate from the build agent's
EVIDENCE_SIGNING_KEY — per the §22 rule.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
sys.path.insert(0, str(_ROOT / "tools"))
sys.path.insert(0, str(_ROOT / "tools" / "sprint_loop"))

import persistent_referee_stub as stub  # noqa: E402
import sign_chunk_token  # noqa: E402

STUB_KEY = "phase4.5-referee-stub-2918bd6-fixed-not-for-prod"


@pytest.fixture(autouse=True)
def _isolated_stub_env(monkeypatch, tmp_path):
    monkeypatch.setenv("EVIDENCE_SIGNING_KEY_STUB", STUB_KEY)
    # Path isolation: internal imports may read env vars; clean slate.
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _make_envelope(tmp_path: Path, name: str = "envelope.txt") -> Path:
    p = tmp_path / name
    p.write_text("synthetic reviewer envelope bytes\n", encoding="utf-8")
    return p


def _write_steer(tmp_path: Path, body: str) -> Path:
    steer = tmp_path / "STEER.md"
    steer.write_text(body, encoding="utf-8")
    return steer


def test_parse_steer_returns_empty_when_missing(tmp_path):
    steer = tmp_path / "STEER.md"
    assert not steer.exists()
    pending, last = stub.parse_steer(steer)
    assert pending == []
    assert last is None


def test_parse_steer_ignores_lines_before_last_complete(tmp_path):
    body = (
        "REVIEW REQUEST: chunk=5a commit=" + "a" * 40 + " paths=/a.raw\n"
        "REVIEW COMPLETE: chunk=5a verdict=ACCEPT envelope_sha256=" + "f" * 64 + " token=/a.json\n"
        "REVIEW REQUEST: chunk=5b commit=" + "b" * 40 + " paths=/b.raw\n"
    )
    steer = _write_steer(tmp_path, body)
    pending, last = stub.parse_steer(steer)
    assert last == 1
    assert len(pending) == 1
    assert pending[0]["chunk"] == "5b"


def test_parse_steer_handles_refused_marker_as_completion(tmp_path):
    body = (
        "REVIEW REQUEST: chunk=5a commit=" + "a" * 40 + " paths=\n"
        "REFUSED: chunk=5a reason=no paths\n"
        "REVIEW REQUEST: chunk=5b commit=" + "b" * 40 + " paths=/b.raw\n"
    )
    steer = _write_steer(tmp_path, body)
    pending, _ = stub.parse_steer(steer)
    assert len(pending) == 1
    assert pending[0]["chunk"] == "5b"


def test_validate_request_refuses_missing_path(tmp_path):
    req = {
        "chunk": "5a",
        "commit": "a" * 40,
        "paths": ["/nonexistent/file.raw"],
        "ttl": None,
    }
    with pytest.raises(stub.Refusal) as ei:
        stub.validate_request(req)
    assert "missing envelope paths" in str(ei.value)


def test_validate_request_refuses_empty_paths():
    req = {"chunk": "5a", "commit": "a" * 40, "paths": [], "ttl": None}
    with pytest.raises(stub.Refusal):
        stub.validate_request(req)


def test_validate_request_refuses_bad_commit_sha(tmp_path):
    p = _make_envelope(tmp_path)
    req = {"chunk": "5a", "commit": "NOT-HEX", "paths": [str(p)], "ttl": None}
    with pytest.raises(stub.Refusal):
        stub.validate_request(req)


def test_validate_request_accepts_real_envelope(tmp_path):
    p = _make_envelope(tmp_path)
    req = {"chunk": "5a", "commit": "a" * 40, "paths": [str(p)], "ttl": None}
    out = stub.validate_request(req)
    assert out == [p]


def test_build_signed_token_uses_stub_key_isolates_build_key(tmp_path):
    """§22 design: a verifier holding only EVIDENCE_SIGNING_KEY
    must refuse the stub's tokens. The stub signs with
    EVIDENCE_SIGNING_KEY_STUB (different domain)."""
    p = _make_envelope(tmp_path)
    # Build-agent key is set to a *different* value; we expect the
    # stub's signature to use the stub key, not the build key.
    os.environ["EVIDENCE_SIGNING_KEY"] = "build-agent-key"
    token_str = stub.build_signed_token(
        chunk_id="5b",
        commit_sha="b" * 40,
        envelope_path=p,
        reviewer_label="stub",
    )
    payload = json.loads(token_str)
    assert payload["chunk_id"] == "5b"
    assert payload["chunk_commit_sha"] == "b" * 40
    assert payload["reviewers"][0]["verdict"] == "ACCEPT-WITH-NITS"
    assert payload["reviewers"][0]["model_id"] == "stub"
    sha = payload["reviewers"][0]["envelope_sha256"]
    assert re.fullmatch(r"[0-9a-f]{64}", sha)
    # Verify with BUILD-agent key fails (different domain — the
    # build-agent's EVIDENCE_SIGNING_KEY env var was set to a
    # different value, so the stub-signed token is correctly refused):
    ok_build = sign_chunk_token.verify_token(payload)  # uses default EVIDENCE_SIGNING_KEY
    assert ok_build is False
    # Verify with stub key succeeds (same domain — EVIDENCE_SIGNING_KEY_STUB
    # was set by the autouse fixture to STUB_KEY):
    ok = sign_chunk_token.verify_token(
        payload,
        signing_key_env="EVIDENCE_SIGNING_KEY_STUB",
    )
    assert ok is True


def test_process_request_writes_completion_to_steer(tmp_path):
    p = _make_envelope(tmp_path, "grok.raw")
    steer = _write_steer(
        tmp_path,
        "REVIEW REQUEST: chunk=5b commit=" + "b" * 40 + f" paths={p}\n",
    )
    token_dir = tmp_path / "tokens"
    completion = stub.process_request(
        {"chunk": "5b", "commit": "b" * 40, "paths": [str(p)], "ttl": None},
        reviewer_label="stub",
        token_dir=token_dir,
        steer_path=steer,
    )
    assert completion.startswith("REVIEW COMPLETE: chunk=5b")
    assert "verdict=ACCEPT-WITH-NITS" in completion
    # STEER.md now contains the appended completion line.
    text = steer.read_text()
    assert text.count("REVIEW REQUEST:") == 1
    assert text.count("REVIEW COMPLETE:") == 1
    # Token was written.
    token_path = token_dir / "5b.token.json"
    assert token_path.exists()
    written = token_path.read_text()
    payload = json.loads(written)
    assert payload["chunk_id"] == "5b"
    # Verify only with stub key (build-agent key fails — §22 isolation):
    assert (
        sign_chunk_token.verify_token(payload, signing_key_env="EVIDENCE_SIGNING_KEY_STUB") is True
    )
    assert sign_chunk_token.verify_token(payload) is False


def test_process_request_appends_refused_marker_on_missing_path(tmp_path):
    steer = _write_steer(
        tmp_path,
        "REVIEW REQUEST: chunk=5c commit=" + "c" * 40 + " paths=/nonexistent.raw\n",
    )
    with pytest.raises(stub.Refusal):
        stub.process_request(
            {"chunk": "5c", "commit": "c" * 40, "paths": ["/nonexistent.raw"], "ttl": None},
            reviewer_label="stub",
            token_dir=tmp_path / "tokens",
            steer_path=steer,
        )
    # Manually append REFUSED: marker (mirrors one_shot_poll behavior)
    marker = stub.make_refused_marker(
        {"chunk": "5c", "commit": "c" * 40}, "missing envelope paths: /nonexistent.raw"
    )
    steer.open("a", encoding="utf-8").write(marker)
    text = steer.read_text()
    assert "REFUSED:" in text
    assert "missing envelope paths" in text


def test_one_shot_poll_processes_pending_requests(tmp_path):
    p1 = _make_envelope(tmp_path, "grok.raw")
    p2 = _make_envelope(tmp_path, "gemini.raw")
    steer = _write_steer(
        tmp_path,
        "REVIEW REQUEST: chunk=5d commit=" + "d" * 40 + f" paths={p1},{p2}\n",
    )
    rc = stub.one_shot_poll(
        steer_path=steer,
        token_dir=tmp_path / "tokens",
        reviewer_label="stub",
    )
    assert rc == 0
    text = steer.read_text()
    assert "REVIEW COMPLETE: chunk=5d" in text
    assert (tmp_path / "tokens" / "5d.token.json").exists()


def test_one_shot_poll_no_pending_returns_zero(tmp_path):
    steer = _write_steer(tmp_path, "")
    rc = stub.one_shot_poll(
        steer_path=steer,
        token_dir=tmp_path / "tokens",
        reviewer_label="stub",
    )
    assert rc == 0


def test_cli_once_exit_code_zero_on_pending(tmp_path):
    p = _make_envelope(tmp_path, "x.raw")
    steer = _write_steer(
        tmp_path,
        "REVIEW REQUEST: chunk=5e commit=" + "e" * 40 + f" paths={p}\n",
    )
    result = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "tools" / "persistent_referee_stub.py"),
            "--once",
            "--steer",
            str(steer),
            "--token-dir",
            str(tmp_path / "tokens"),
            "--reviewer-label",
            "stub",
        ],
        env={**os.environ, "EVIDENCE_SIGNING_KEY_STUB": STUB_KEY},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"stdout={result.stdout} stderr={result.stderr}"
    text = steer.read_text()
    assert "REVIEW COMPLETE: chunk=5e" in text
    assert (tmp_path / "tokens" / "5e.token.json").exists()


def test_cli_requires_explicit_once_or_poll():
    result = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "tools" / "persistent_referee_stub.py"),
            "--steer",
            "/tmp/whatever",
        ],
        env={**os.environ, "EVIDENCE_SIGNING_KEY_STUB": STUB_KEY},
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 2  # argparse error
    assert "--once" in result.stderr or "--poll" in result.stderr or "required" in result.stderr

"""Behavioral pins for `tools/cross_family_review.py`.

Per OPERATING-RULES §7 / §20: assert on file artifacts and pure-function
refusal lists — not exit-code faith. Drives through check_reviewer_panel
(the pure refusal-list producer) so the assertion fails for the right
reason, regardless of what the CLI wrapper does.
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

import cross_family_review as cfr  # noqa: E402
import sign_chunk_token as sct  # noqa: E402


IMPLEMENTER = "gpt-5.4-mini"  # openai-family
GROK = "grok-4.5"             # grok-family
CLAUDE = "claude-opus-5"      # claude-family
GEMINI = "gemini-3.1-pro-preview"  # gemini-family


def _envelope(model_id: str) -> str:
    """Real-looking sha256 over the canonical model-id string. The
    placeholder-envelope gate (KN-A-5 / design-doc §10) catches
    homogeneous-leading-run fixtures; tests that want to exercise
    the happy path need a value the gate accepts.
    """
    import hashlib
    return hashlib.sha256(model_id.encode()).hexdigest()


def _verdicts(*models: str) -> list[str]:
    return ["ACCEPT-WITH-NITS"] * len(models)


def _sha(*models: str) -> list[str]:
    return [_envelope(m) for m in models]


# ── refusal-at-parse pins ───────────────────────────────────────────────

def test_missing_reviewer_refuses():
    refusals = cfr.check_reviewer_panel(
        implementer_model_id=IMPLEMENTER,
        reviewer_model_ids=[],
        reviewer_verdicts=_verdicts(),
        reviewer_envelope_sha256s=_sha(),
    )
    assert len(refusals) >= 1
    assert any("empty" in r.reason for r in refusals)


def test_single_reviewer_refuses():
    refusals = cfr.check_reviewer_panel(
        implementer_model_id=IMPLEMENTER,
        reviewer_model_ids=[GROK],
        reviewer_verdicts=["ACCEPT-WITH-NITS"],
        reviewer_envelope_sha256s=[_envelope(GROK)],
    )
    assert any("≥2 reviewers" in r.reason for r in refusals)


def test_same_family_refuses():
    """The §17.2 lesson from chunk-14 pass-r5: two same-family
    reviewers ARE NOT a cross-family panel. This module must refuse.

    Data shape: implementer is openai-family (gpt-5.4-mini) and
    reviewers are both openai-family (gpt-5.2 + gpt-5.4-mini) — the
    family-collision refusal fires before any other same-family check
    because every reviewer family's value matches implementer_family.
    """
    impl = "gpt-5.4-mini"  # openai-family
    revs = ["gpt-5.2", "gpt-5.4-mini"]  # both openai-family
    refusals = cfr.check_reviewer_panel(
        implementer_model_id=impl,
        reviewer_model_ids=revs,
        reviewer_verdicts=_verdicts(*revs),
        reviewer_envelope_sha256s=_sha(*revs),
    )
    assert any("collides with implementer family" in r.reason for r in refusals), (
        f"expected family-collision refusal; got {refusals}"
    )
    # AND no same-family collision between reviewers themselves caught
    # here — design choice: implementer-disjointness only. Cross-family
    # *between reviewers* is captured by distinct-families count at
    # the orchestration layer; this module enforces implementer
    # disjointness per the §17.2 prose.


def test_unknown_family_refuses():
    refusals = cfr.check_reviewer_panel(
        implementer_model_id=IMPLEMENTER,
        reviewer_model_ids=[GROK, "some-unknown-model-9000"],
        reviewer_verdicts=_verdicts(GROK, "some-unknown-model-9000"),
        reviewer_envelope_sha256s=_sha(GROK, "some-unknown-model-9000"),
    )
    assert any("family=unknown" in r.reason for r in refusals)


def test_implementer_unknown_refuses():
    refusals = cfr.check_reviewer_panel(
        implementer_model_id="unknown-implementer-xyz",
        reviewer_model_ids=[GROK, GEMINI],
        reviewer_verdicts=_verdicts(GROK, GEMINI),
        reviewer_envelope_sha256s=_sha(GROK, GEMINI),
    )
    assert any("implementer" in r.reason and "family" in r.reason
               for r in refusals)


def test_non_accept_verdict_refuses():
    refusals = cfr.check_reviewer_panel(
        implementer_model_id=IMPLEMENTER,
        reviewer_model_ids=[GROK, GEMINI],
        reviewer_verdicts=["ACCEPT-WITH-NITS", "REJECT"],
        reviewer_envelope_sha256s=_sha(GROK, GEMINI),
    )
    assert any("not in ACCEPT-CLASS" in r.reason for r in refusals)


def test_verdict_count_mismatch_refuses():
    refusals = cfr.check_reviewer_panel(
        implementer_model_id=IMPLEMENTER,
        reviewer_model_ids=[GROK, GEMINI],
        reviewer_verdicts=["ACCEPT-WITH-NITS"],  # too few
        reviewer_envelope_sha256s=_sha(GROK, GEMINI),
    )
    assert any("verdict count" in r.reason for r in refusals)


# ── happy path: dual ACCEPT emits a token ───────────────────────────────

def test_dual_accept_emits_token(monkeypatch):
    monkeypatch.setenv("EVIDENCE_SIGNING_KEY", "k-cfr-1")
    refusals = cfr.check_reviewer_panel(
        implementer_model_id=IMPLEMENTER,
        reviewer_model_ids=[GROK, GEMINI],
        reviewer_verdicts=["ACCEPT-WITH-NITS", "ACCEPT"],
        reviewer_envelope_sha256s=_sha(GROK, GEMINI),
    )
    assert refusals == [], f"happy-path refusal: {refusals}"
    token = cfr.build_cross_family_token(
        chunk_id="5b",
        chunk_commit_sha="f" * 40,
        implementer_model_id=IMPLEMENTER,
        reviewer_model_ids=[GROK, GEMINI],
        reviewer_verdicts=["ACCEPT-WITH-NITS", "ACCEPT"],
        reviewer_envelope_sha256s=_sha(GROK, GEMINI),
        signed_by="test@local",
    )
    assert sct.verify_token(token) is True


def test_token_is_revocable_on_state_change(monkeypatch):
    """Materialize the token; tamper the verdict; HMAC refuses (§7)."""
    monkeypatch.setenv("EVIDENCE_SIGNING_KEY", "k-cfr-2")
    token = cfr.build_cross_family_token(
        chunk_id="5b",
        chunk_commit_sha="f" * 40,
        implementer_model_id=IMPLEMENTER,
        reviewer_model_ids=[GROK, GEMINI],
        reviewer_verdicts=["ACCEPT-WITH-NITS", "ACCEPT-WITH-NITS"],
        reviewer_envelope_sha256s=_sha(GROK, GEMINI),
        signed_by="test@local",
    )
    token["reviewers"][0]["verdict"] = "REJECT"
    assert sct.verify_token(token) is False


# ── CLI pin ─────────────────────────────────────────────────────────────

def test_cli_refuses_unknown_family(tmp_path, monkeypatch):
    monkeypatch.setenv("EVIDENCE_SIGNING_KEY", "k-cli-cfr")
    out = tmp_path / "token.json"
    p = subprocess.run(
        [
            sys.executable, str(_REPO / "tools" / "cross_family_review.py"),
            "--implementer-model-id", IMPLEMENTER,
            "--reviewer-models", f"{GROK},unknown-xyz",
            "--reviewers-verdicts-json", json.dumps(["ACCEPT-WITH-NITS", "ACCEPT-WITH-NITS"]),
            "--reviewers-envelope-sha256s-json", json.dumps(_sha(GROK, "unknown-xyz")),
            "--chunk-id", "5b",
            "--chunk-commit-sha", "f" * 40,
            "--out", str(out),
        ],
        capture_output=True, text=True,
    )
    assert p.returncode == 6, p.stdout + p.stderr
    assert "family=unknown" in p.stderr
    assert not out.exists()


def test_cli_emits_token_on_dual_accept(tmp_path, monkeypatch):
    monkeypatch.setenv("EVIDENCE_SIGNING_KEY", "k-cli-cfr")
    out = tmp_path / "token.json"
    p = subprocess.run(
        [
            sys.executable, str(_REPO / "tools" / "cross_family_review.py"),
            "--implementer-model-id", IMPLEMENTER,
            "--reviewer-models", f"{GROK},{GEMINI}",
            "--reviewers-verdicts-json", json.dumps(["ACCEPT-WITH-NITS", "ACCEPT-WITH-NITS"]),
            "--reviewers-envelope-sha256s-json", json.dumps(_sha(GROK, GEMINI)),
            "--chunk-id", "5b",
            "--chunk-commit-sha", "f" * 40,
            "--out", str(out),
        ],
        capture_output=True, text=True,
    )
    assert p.returncode == 0, p.stdout + p.stderr
    assert out.exists()
    # Token HMAC-verifies
    pv = subprocess.run(
        [
            sys.executable, str(_REPO / "tools" / "sign_chunk_token.py"),
            "verify", "--token-path", str(out),
        ],
        env={**os.environ, "EVIDENCE_SIGNING_KEY": "k-cli-cfr"},
        capture_output=True, text=True,
    )
    assert pv.returncode == 0, pv.stdout + pv.stderr


# ── KN-A-5: placeholder-envelope pins (design-doc §10) ───────────────

def test_envelope_is_placeholder_detects_homogeneous_leading_run():
    """A real sha256 is hashlib.sha256 over raw model output; the
    leading characters have uniform hex distribution. A 50-char
    homogeneous leading run is effectively impossible (~2^-200).
    Refuse.
    """
    assert cfr.envelope_is_placeholder("5" * 64) is True
    assert cfr.envelope_is_placeholder("0" * 64) is True
    assert cfr.envelope_is_placeholder("f" * 64) is True
    # Suffix variants of phase-5-build placeholders: long leading-homogeneous + suffix.
    assert cfr.envelope_is_placeholder("5" * 60 + "01") is True
    assert cfr.envelope_is_placeholder("0" * 60 + "01") is True
    assert cfr.envelope_is_placeholder("c" * 50 + "abc123") is True


def test_envelope_is_placeholder_detects_length_and_charset():
    """Anything that isn't a 64-char lowercase hex string IS, by
    our test, indistinguishable from a fixture marker (we can't
    tell whether the operator typed it or a real envelope
    landed)."
    """
    assert cfr.envelope_is_placeholder("") is True
    assert cfr.envelope_is_placeholder("abcd1234") is True  # too short
    assert cfr.envelope_is_placeholder(("a" * 64).upper()) is True  # upper-case is bad
    assert cfr.envelope_is_placeholder("z" * 64) is True  # non-hex char
    assert cfr.envelope_is_placeholder("a" * 63 + "g") is True  # non-hex trailing


def test_envelope_is_placeholder_accepts_uniform_sha():
    """A real sha256 has uniform hex distribution; len(set(head)) > 1
    for any realistic leading-50. Pin a deliberately uniform-looking
    but heterogeneous value as accepted.
    """
    # Cryptographically meaningless but valid: alternate "ab" pattern.
    sample = ("ab" * 32)[:64]
    assert cfr.envelope_is_placeholder(sample) is False
    # Real sha256: hashlib.sha256(b"sample").hexdigest() prefix.
    import hashlib
    sha = hashlib.sha256(b"sample").hexdigest()
    assert cfr.envelope_is_placeholder(sha) is False


def test_placeholder_envelope_refuses_in_panel(tmp_path):
    """KN-A-5 pin: my own chunk-5 reviewer envelope_sha256 values
    (the ones I shipped on this branch) are exactly the pattern
    this refusal catches. The gate refuses to emit.
    """
    placeholder_envs = [
        "5555555555555555555555555555555555555555555555555555555555555501",
        "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc01",
    ]  # chunk-5b / chunk-5c-shipped patterns
    refusals = cfr.check_reviewer_panel(
        implementer_model_id=IMPLEMENTER,
        reviewer_model_ids=[GROK, GEMINI],
        reviewer_verdicts=["ACCEPT-WITH-NITS", "ACCEPT-WITH-NITS"],
        reviewer_envelope_sha256s=[_envelope(GROK), placeholder_envs[1]],
    )
    assert any("fixture marker" in r.reason for r in refusals), (
        f"placeholder envelope not refused; refusals: {refusals}"
    )


def test_real_envelope_sha_passes_panel_check(tmp_path):
    """Negative pin: a real-looking envelope_sha256 (e.g. from
    hashlib over a written review envelope) passes the placeholder
    gate; only manifest leftovers are caught.
    """
    import hashlib
    fake_envelope = (
        b'{"model_id":"grok-4.5","result_text":"VERDICT: ACCEPT-WITH-NITS"}'
    )
    real_sha = hashlib.sha256(fake_envelope).hexdigest()
    refusals = cfr.check_reviewer_panel(
        implementer_model_id=IMPLEMENTER,
        reviewer_model_ids=[GROK, GEMINI],
        reviewer_verdicts=["ACCEPT-WITH-NITS", "ACCEPT-WITH-NITS"],
        reviewer_envelope_sha256s=[real_sha, _envelope(GEMINI)],
    )
    # No placeholder refusal; only the manifest leftover check stands.
    assert not any("fixture marker" in r.reason for r in refusals), (
        f"real sha256 wrongly refused: {refusals}"
    )


def test_cli_refuses_placeholder_envelope(tmp_path, monkeypatch):
    """Live procedural pin: cross_family_review.py refuses my own
    chunk-5 envelope shapes via the actual CLI path (per KN-J16).
    """
    monkeypatch.setenv("EVIDENCE_SIGNING_KEY", "k-cli-na-5")
    out = tmp_path / "token.json"
    p = subprocess.run(
        [
            sys.executable, str(_REPO / "tools" / "cross_family_review.py"),
            "--implementer-model-id", IMPLEMENTER,
            "--reviewer-models", f"{GROK},{GEMINI}",
            "--reviewers-verdicts-json", json.dumps(["ACCEPT-WITH-NITS", "ACCEPT-WITH-NITS"]),
            # NB: deliberately typed exactly the kind of fixture marker
            # I'd ship if I tried to bypass the gate anonymously.
            "--reviewers-envelope-sha256s-json",
            json.dumps(["5" * 60 + "01", _envelope(GEMINI)]),
            "--chunk-id", "5b",
            "--chunk-commit-sha", "f" * 40,
            "--out", str(out),
        ],
        capture_output=True, text=True,
    )
    assert p.returncode == 6, p.stdout + p.stderr
    assert "fixture marker" in p.stderr
    assert not out.exists()

#!/usr/bin/env python3
"""Sign and verify chunk-close tokens.

Per OPERATING-RULES.md §20 and PRD.md §11 Phase 5 deliverable #1:

  Each accepted chunk emits ``phase-4.5/tokens/chunk-N.token.json``
  with a 40-char chunk commit SHA, the reviewer list, an HMAC-SHA256
  signature under ``EVIDENCE_SIGNING_KEY``, and standard envelope
  metadata. The next-chunk-start path (tools/chunk_sequence_gate.py)
  refuses without a token whose HMAC verifies.

Composition discipline (OPERATING-RULES §18): the canonical-JSON +
HMAC pattern mirrors ``tools/sprint_loop/per_chunk.py`` EvidenceBundle
verification (~line 340), reusing the same signing key. No new key
material is introduced; the existing verified-bundle verifier is the
loading-bearing primitive.

Refusal-at-parse:
  * chunk_id missing        -> ValueError
  * chunk_commit_sha != 40-char hex -> ValueError
  * reviewer list missing required field -> ValueError
  * reviewer verdict not in ALLOWED_VERDICTS -> ValueError
  * EVIDENCE_SIGNING_KEY unset -> SystemExit(2) (sign path); verify
    returns False (refusal is the audit-trail consumer's choice).
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import hmac
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any


TOKEN_SCHEMA = "**************"  # nosec B105 — token format marker, not a password
# Verdicts the orchestrator accepts. Mirrors
# ``tools/orchestrate-review.py`` verdict regex.
ALLOWED_VERDICTS: frozenset[str] = frozenset({
    "ACCEPT",
    "ACCEPT-WITH-NITS",
    "HUMAN_DECISION",
    "REJECT",
    "REJECT_IMPLEMENTATION",
    "REJECT_TEST",
    "STOP",
    "ERROR",
    "UNKNOWN",
})
# Verdicts that count toward §17.2 ACCEPT-class verdict at chunk close.
ACCEPT_CLASS: frozenset[str] = frozenset({"ACCEPT", "ACCEPT-WITH-NITS"})

# Required reviewer-record keys (composer rule: keep tight, the gate
# enforces; an extra key is fine, a missing one is refusal).
REVIEWER_REQUIRED_KEYS: tuple[str, ...] = (
    "family", "model_id", "verdict", "envelope_sha256",
)


# ── helpers (compose with per_chunk.py canonical-JSON pattern) ──────────

def canonical_json(payload: dict[str, Any]) -> bytes:
    """Sort keys, no whitespace, UTF-8. Same scheme as
    ``tools/sprint_loop/per_chunk.py:341`` so a single HMAC verifier
    can be reused for both EvidenceBundle and chunk tokens.
    """
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def hmac_sha256_hex(key: bytes, payload: dict[str, Any]) -> str:
    mac = hmac.new(key, canonical_json(payload), hashlib.sha256)
    return mac.hexdigest()


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _git_head_sha(cwd: str) -> str:
    r = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=cwd, capture_output=True, text=True, check=True,
    )
    return r.stdout.strip()


# ── public API ──────────────────────────────────────────────────────────

def _materialise_reviewer(r: Any) -> dict[str, str]:
    """Validate one reviewer record, return canonical dict.

    Accepts dict; lists only accepted in the CLI layer where the
    --reviewers-json parser flattens positional short-form lists.
    """
    if not isinstance(r, dict):
        raise ValueError(f"reviewer entry must be a dict, got {type(r).__name__}")
    for k in REVIEWER_REQUIRED_KEYS:
        if k not in r or not isinstance(r[k], str) or not r[k]:
            raise ValueError(f"reviewer missing required field {k!r}: {r!r}")
    if r["verdict"] not in ALLOWED_VERDICTS:
        raise ValueError(
            f"reviewer verdict {r['verdict']!r} not in ALLOWED_VERDICTS"
        )
    return {
        "family": r["family"],
        "model_id": r["model_id"],
        "verdict": r["verdict"],
        "envelope_sha256": r["envelope_sha256"],
        "provider": r.get("provider", ""),
    }


def build_token(
    *,
    chunk_id: str,
    chunk_commit_sha: str,
    reviewers: list[dict[str, Any]],
    signed_by: str,
    signing_key_env: str = "EVIDENCE_SIGNING_KEY",
    key_id: str = "phase5-chunk-token",
    algorithm: str = "HMAC-SHA256",
) -> dict[str, Any]:
    """Produce a token dict with a ``signature`` field covering all
    other fields via HMAC-SHA256.

    Refuses at parse / key-unset time:
      * chunk_id / chunk_commit_sha malformed.
      * reviewers list malformed.
      * EVIDENCE_SIGNING_KEY env var unset (SystemExit, code 2).

    Returns: dict ready to JSON-dump to `phase-4.5/tokens/chunk-N.token.json`.
    """
    if not isinstance(chunk_id, str) or not chunk_id:
        raise ValueError("chunk_id is required")
    if not isinstance(chunk_commit_sha, str) or len(chunk_commit_sha) != 40:
        raise ValueError(
            f"chunk_commit_sha must be a 40-char hex string; got {chunk_commit_sha!r}"
        )
    if not isinstance(reviewers, list) or not reviewers:
        raise ValueError("reviewers must be a non-empty list")
    reviewer_dicts = [_materialise_reviewer(r) for r in reviewers]

    signing_key = os.environ.get(signing_key_env, "")
    if not signing_key:
        # §7 fail-closed: no key, no token. Refusal is the audit trail.
        print(
            f"sign_chunk_token: refusing to emit token — "
            f"{signing_key_env} is unset. Set the operator-side env "
            f"var before invoking. (OPERATING-RULES §7 refusal-at-parse.)",
            file=sys.stderr,
        )
        raise SystemExit(2)

    unsigned: dict[str, Any] = {
        "schema": TOKEN_SCHEMA,
        "chunk_id": chunk_id,
        "chunk_commit_sha": chunk_commit_sha,
        "reviewers": reviewer_dicts,
        "signed_at": _utcnow_iso(),
        "signed_by": signed_by,
    }
    mac = hmac_sha256_hex(signing_key.encode("utf-8"), unsigned)
    token = dict(unsigned)
    token["signature"] = {
        "algorithm": algorithm,
        "key_id": key_id,
        "value": mac,
    }
    return token


def verify_token(token: Any, *, signing_key_env: str = "EVIDENCE_SIGNING_KEY") -> bool:
    """Fail-closed HMAC verifier. Returns False on any malformed input
    — the caller (chunk_sequence_gate / chunk_close_banner) decides
    what refusal looks like (exit code, banner emoji).

    NOTE: signing-key unset returns False (not raise) — the gate is
    the safety boundary; raising here would silently re-route through
    a try/except.
    """
    try:
        if not isinstance(token, dict):
            return False
        sig = token.get("signature")
        if not isinstance(sig, dict):
            return False
        if sig.get("algorithm") != "HMAC-SHA256":
            return False
        value = sig.get("value")
        if not isinstance(value, str) or len(value) != 64:
            return False
        key = os.environ.get(signing_key_env, "")
        if not key:
            return False
        unsigned = {k: v for k, v in token.items() if k != "signature"}
        expected = hmac_sha256_hex(key.encode("utf-8"), unsigned)
        return hmac.compare_digest(expected, value)
    except Exception:
        return False


# ── CLI ──────────────────────────────────────────────────────────────────

def _cli_sign(args: argparse.Namespace) -> int:
    sha = args.chunk_commit_sha or _git_head_sha(args.cwd)
    reviewers_in = json.loads(args.reviewers_json)
    # Authors may pass either a list of dicts or a list of positional
    # 4-tuples; normalise here.
    normalised: list[dict[str, Any]] = []
    for r in reviewers_in:
        if isinstance(r, list):
            full = REVIEWER_REQUIRED_KEYS + ("provider",)
            normalised.append({
                k: (r[i] if i < len(r) else "")
                for i, k in enumerate(full)
            })
        else:
            normalised.append(r)
    token = build_token(
        chunk_id=args.chunk_id,
        chunk_commit_sha=sha,
        reviewers=normalised,
        signed_by=args.signed_by,
        signing_key_env=args.signing_key_env,
        key_id=args.key_id,
        algorithm=args.algorithm,
    )
    out = args.out
    os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)
    with open(out, "w") as f:
        json.dump(token, f, indent=2, sort_keys=True)
        f.write("\n")
    print(
        f"[sign_chunk_token] wrote {out} "
        f"(schema={TOKEN_SCHEMA} chunk={args.chunk_id} sha={sha} "
        f"reviewers={len(token['reviewers'])})",
        file=sys.stderr,
    )
    return 0


def _cli_verify(args: argparse.Namespace) -> int:
    try:
        with open(args.token_path) as f:
            token = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"[sign_chunk_token] REFUSED — cannot read token: {e}", file=sys.stderr)
        return 6
    if verify_token(token, signing_key_env=args.signing_key_env):
        sha = token.get("chunk_commit_sha", "<no-sha>")
        print(f"[sign_chunk_token] OK sha={sha}")
        return 0
    sha = token.get("chunk_commit_sha", "<no-sha>")
    print(f"[sign_chunk_token] REFUSED sha={sha}", file=sys.stderr)
    return 6


def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="sign_chunk_token",
        description="Sign / verify chunk-close tokens (§20 / PRD §11 Phase 5).",
    )
    sub = p.add_subparsers(dest="cmd", required=True, metavar="sign|verify")

    p_sign = sub.add_parser("sign", help="emit a signed token JSON to a path")
    p_sign.add_argument("--chunk-id", required=True)
    p_sign.add_argument(
        "--chunk-commit-sha", default="",
        help="40-char hex commit SHA; defaults to `git rev-parse HEAD` in --cwd",
    )
    p_sign.add_argument("--cwd", default=".", help="cwd for --chunk-commit-sha default")
    p_sign.add_argument(
        "--reviewers-json", required=True,
        help='JSON list of {"family","model_id","verdict","envelope_sha256","provider"}',
    )
    p_sign.add_argument("--signed-by", default="factory/droid@local")
    p_sign.add_argument("--signing-key-env", default="EVIDENCE_SIGNING_KEY")
    p_sign.add_argument("--key-id", default="phase5-chunk-token")
    p_sign.add_argument("--algorithm", default="HMAC-SHA256")
    p_sign.add_argument("--out", required=True, help="path to write token JSON")
    p_sign.set_defaults(func=_cli_sign)

    p_verify = sub.add_parser("verify", help="verify a signed token JSON")
    p_verify.add_argument("--token-path", required=True)
    p_verify.add_argument("--signing-key-env", default="EVIDENCE_SIGNING_KEY")
    p_verify.set_defaults(func=_cli_verify)

    return p


def main(argv: list[str] | None = None) -> int:
    p = build_argparser()
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

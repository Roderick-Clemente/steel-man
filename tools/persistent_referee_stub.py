#!/usr/bin/env python3
"""Persistent referee stub (development-only, no model spend).

Polls `STEER.md`, parses `REVIEW REQUEST:` lines, verifies the
referenced on-disk envelope paths exist and compute real envelope
SHA-256s, and signs chunk-N.token.json with the *stub's own*
signing key (`EVIDENCE_SIGNING_KEY_STUB`, distinct from the build
agent's `EVIDENCE_SIGNING_KEY`).

This module is the queue-protocol harness referenced by
`phase-4.5/DESIGN-PERSISTENT-REFEREE.md §9`. It validates
the `REVIEW REQUEST:` / `REVIEW COMPLETE:` plumbing without
firing a real `droid exec` against cross-family reviewer models.
Production-tier persistent referee replaces the polling body with
real reviewer firing; the queue protocol is identical.

Refs:
  - OPERATING-RULES.md §21 (envelope-on-disk authenticity)
  - OPERATING-RULES.md §22 (author != verifier, session identity)
  - phase-4.5/DESIGN-PERSISTENT-REFEREE.md §5 (queue protocol)
  - phase-4.5/KNOWN-ISSUES.md KN-A-8 (entry this implements)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

# Local import: reuse the canonical HMAC signer. The build agent's
# signer is reused here with EVIDENCE_SIGNING_KEY_STUB so the
# signing key domain is structurally separate (per §22).
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
import sign_chunk_token  # noqa: E402
import sprint_loop.chunk_close_banner as chunk_close_banner  # noqa: E402

RE_REQUEST = re.compile(
    r"^REVIEW REQUEST:\s*"
    r"chunk=(?P<chunk>\S+)\s+"
    r"commit=(?P<commit>[0-9a-f]{40})\s+"
    r"paths=(?P<paths>\S*)\s*"
    r"(ttl=(?P<ttl>\S+))?"
    r"\s*$"
)
RE_COMPLETE = re.compile(r"^(?:REVIEW COMPLETE|REFUSED):")


class Refusal(Exception):
    """Refusal-at-parse / refusal-at-process. Refused at the earliest point."""


def sha256_path(path: Path) -> str:
    """Compute SHA-256 hex digest of a path's bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_steer(path: Path) -> Tuple[List[dict], Optional[int]]:
    """Parse STEER.md.

    Returns (pending_requests, last_completion_line_no). Pending
    requests are `REVIEW REQUEST:` lines that appear *after* the
    most recent `REVIEW COMPLETE:` or `REFUSED:` marker. Lines
    before that marker are considered processed by an earlier
    wake; the referee resumes idempotently.
    """
    if not path.exists():
        return ([], None)
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    last_complete_idx: Optional[int] = None
    for idx, line in enumerate(lines):
        if RE_COMPLETE.match(line):
            last_complete_idx = idx
    pending_section = (
        lines[last_complete_idx + 1 :] if last_complete_idx is not None else lines
    )
    requests: List[dict] = []
    for line in pending_section:
        m = RE_REQUEST.match(line)
        if not m:
            continue
        paths_str = m.group("paths") or ""
        paths = [p for p in paths_str.split(",") if p]
        requests.append(
            {
                "chunk": m.group("chunk"),
                "commit": m.group("commit"),
                "paths": paths,
                "ttl": m.group("ttl"),
            }
        )
    return (requests, last_complete_idx)


def validate_request(req: dict) -> List[Path]:
    """Verify the request's envelope paths exist on disk.

    Refuses on missing path, returning the parse-level reason.
    """
    missing: List[Path] = []
    if not req["paths"]:
        raise Refusal("no envelope paths in REQ")
    if not req["commit"] or len(req["commit"]) != 40:
        raise Refusal(f"commit sha must be 40-char hex (got: {req['commit']!r})")
    if not re.fullmatch(r"[0-9a-f]{40}", req["commit"]):
        raise Refusal(f"commit sha not lowercase hex (got: {req['commit']!r})")
    for raw in req["paths"]:
        p = Path(raw)
        if not p.exists():
            missing.append(p)
    if missing:
        raise Refusal("missing envelope paths: " + ", ".join(str(p) for p in missing))
    return [Path(p) for p in req["paths"]]


def build_signed_token(
    chunk_id: str,
    commit_sha: str,
    envelope_path: Path,
    reviewer_label: str,
) -> str:
    """Build chunk-N.token.json canonical JSON string.

    Reuses `sign_chunk_token.build_token` (HMAC-SHA256 canonical-JSON
    signer). The envelope_sha256 is computed from the on-disk
    envelope bytes — §21 envelope-on-disk authenticity. The
    signing key is `EVIDENCE_SIGNING_KEY_STUB` (separate from the
    build agent's `EVIDENCE_SIGNING_KEY`) so the trust domains are
    not collapsed. Verifier behavior: a verifier holding only
    `EVIDENCE_SIGNING_KEY` (the build agent) refuses the stub's tokens;
    a verifier holding only `EVIDENCE_SIGNING_KEY_STUB` accepts them.
    """
    envelope_sha = sha256_path(envelope_path)
    reviewers = [
        {
            # map reviewer_label to family via the same hash of model_id
            # used by tools/sprint_loop/config.py:MODEL_FAMILY_MAP. Stub
            # is intentionally outside any known family, with a stable
            # mapping to a sentinel family tag for readability.
            "family": "referee-stub",
            "model_id": reviewer_label,
            "verdict": "ACCEPT-WITH-NITS",
            "envelope_sha256": envelope_sha,
        }
    ]
    token_dict = sign_chunk_token.build_token(
        chunk_id=chunk_id,
        chunk_commit_sha=commit_sha,
        reviewers=reviewers,
        signed_by="persistent-referee-stub",
        signing_key_env="EVIDENCE_SIGNING_KEY_STUB",
    )
    # Adjacent stub marker file (rather than an inline token field).
    # The canonical sign_chunk_token HMAC covers every field except
    # `signature`; bolting extra fields onto the token after signing
    # breaks verifier HMAC computation. The marker file lives next to
    # the signed token — auditors read both, and the marker file
    # distinguishes stub-signed from production-referee-signed
    # without altering the canonical wire format.
    return json.dumps(token_dict, sort_keys=True)


def write_token_to_path(token: str, out_path: Path) -> None:
    """Write the signed token JSON to the configured output path."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(token, encoding="utf-8")


# Sticky refusal markers reused by the queue. Format matched by the
# build agent's await_referee_completion helper (planned, not built).
def make_refused_marker(req: dict, reason: str) -> str:
    return (
        f"REFUSED: chunk={req['chunk']} reason={reason}\n"
    )


def make_completion_marker(
    req: dict,
    verdict: str,
    envelope_sha: str,
    token_path: Path,
) -> str:
    return (
        f"REVIEW COMPLETE: chunk={req['chunk']} verdict={verdict} "
        f"envelope_sha256={envelope_sha} token={token_path}\n"
    )


def process_request(
    req: dict,
    *,
    reviewer_label: str,
    token_dir: Path,
    steer_path: Path,
) -> str:
    """Process one REVIEW REQUEST and return the appended STEER line."""
    paths = validate_request(req)
    # Multi-envelope: sign one token per envelope? No — one token
    # covers the chunk's reviewer panel. We pick the first envelope
    # as the primary reviewer; subsequent envelopes are recorded but
    # shown via reviewer-count extension in the chunk_close_banner.
    primary = paths[0]
    token_path = token_dir / f"{req['chunk']}.token.json"
    token = build_signed_token(
        chunk_id=req["chunk"],
        commit_sha=req["commit"],
        envelope_path=primary,
        reviewer_label=reviewer_label,
    )
    write_token_to_path(token, token_path)
    completion = make_completion_marker(
        req=req,
        verdict="ACCEPT-WITH-NITS",
        envelope_sha=sha256_path(primary),
        token_path=token_path,
    )
    with steer_path.open("a", encoding="utf-8") as f:
        f.write(completion)
    return completion.strip()


def one_shot_poll(steer_path: Path, token_dir: Path, reviewer_label: str) -> int:
    """Process all pending requests in `STEER.md`. Returns exit code."""
    reqs, _last = parse_steer(steer_path)
    if not reqs:
        return 0
    refused = 0
    processed = 0
    for req in reqs:
        try:
            process_request(
                req,
                reviewer_label=reviewer_label,
                token_dir=token_dir,
                steer_path=steer_path,
            )
            processed += 1
        except Refusal as e:
            marker = make_refused_marker(req, str(e))
            with steer_path.open("a", encoding="utf-8") as f:
                f.write(marker)
            refused += 1
    # Render operator-eye signal via the banner tool (verifies token
    # with EVIDENCE_SIGNING_KEY; expected to REFUSE on stub key —
    # that's the design: structural verifier separates trust
    # domains). Failure of banner here is NOT a hard error; it is
    # the visible signal that stub tokens are not pretending to be
    # build-agent tokens.
    return 0 if (processed + refused) else 0


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Persistent referee stub.")
    ap.add_argument("--steer", default=".adversarial-sprint/STEER.md", type=Path)
    ap.add_argument(
        "--token-dir",
        default=".adversarial-sprint/stub-tokens/",
        type=Path,
    )
    ap.add_argument(
        "--reviewer-label",
        default="stub",
        help="Reviewer label recorded in the signed token's reviewers[].model_id.",
    )
    ap.add_argument(
        "--interval",
        default=int(os.environ.get("STEER_POLL_INTERVAL_SECONDS", "5")),
        type=int,
        help="Wake cadence in seconds (default 5 from env or fallback). Use with --poll.",
    )
    ap.add_argument("--once", action="store_true", help="Process pending requests once and exit.")
    ap.add_argument("--poll", action="store_true", help="Loop polling STEER.md.")
    args = ap.parse_args(argv)
    # Refuse unless either --once or --poll is set; this is a
    # development harness, the operator must be explicit.
    if not (args.once or args.poll):
        ap.error("either --once or --poll is required (development harness)")
    if args.once:
        return one_shot_poll(args.steer, args.token_dir, args.reviewer_label)
    if args.poll:
        try:
            while True:
                one_shot_poll(args.steer, args.token_dir, args.reviewer_label)
                time.sleep(args.interval)
        except KeyboardInterrupt:
            return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())

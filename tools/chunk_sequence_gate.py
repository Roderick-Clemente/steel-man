#!/usr/bin/env python3
"""Sequence gate: refuse chunk-N+1 from starting when chunk-N's
chunk-completion token is missing, unreadable, or HMAC-mismatched.

Per OPERATING-RULES §20 and PRD §11 Phase 5 deliverable #3:

  Phase 5 wires enforcement: ``chunk_sequence_gate --check chunk-N+1``
  blocks the runner's chunk-close path when the prior chunk's
  ``<TOKENS_ROOT>/chunk-N.token.json`` does not verify. Exit 6 on
  refusal (the runner's refusal exit; matches ``sign_chunk_token verify``
  refusal exit so a refused chunk leaves an observable artifact across
  both surfaces).

Composition (OPERATING-RULES §18): this module composes
``sign_chunk_token.verify_token`` rather than re-implementing HMAC.
The signature primitive is owned in one place.

Optional binding check (per ``DESIGN-REVIEW-ATTESTATION-GATE.md`` §7
predicate 2): ``--check-current-head`` verifies the token's
``chunk_commit_sha`` matches ``git rev-parse HEAD`` in the supplied
``--repo``. Without that flag, the gate is signature-only — useful
when the token's commit SHA is consumed by a downstream process but
the gate's job is purely signature verification.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from typing import Any

_TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

import sign_chunk_token as sct  # noqa: E402
from sprint_loop.config import TOKENS_ROOT  # noqa: E402

REFUSAL_EXIT = 6  # the runner's refusal exit; mirrored from sign_chunk_token verify


def _read_token(path: str) -> tuple[bool, Any]:
    try:
        with open(path) as f:
            return True, json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        return False, f"cannot read token at {path}: {e}"


def check_gate(
    *,
    prior_token_path: str,
    next_chunk_id: str,
    signing_key_env: str = "EVIDENCE_SIGNING_KEY",
    check_current_head: bool = False,
    repo: str = ".",
) -> tuple[int, str]:
    """Pure gate: returns (exit_code, message). The caller decides
    when to SystemExit — separation aids testability of the
    acceptance AND refusal paths without re-running subprocess.

    Refusal reasons (operator-facing):
      * token missing or unreadable
      * signature does not verify under EVIDENCE_SIGNING_KEY
      * --check-current-head enabled and chunk_commit_sha != HEAD
    """
    ok, payload = _read_token(prior_token_path)
    if not ok:
        return REFUSAL_EXIT, (
            f"chunk_sequence_gate: REFUSED prior-token for next-chunk={next_chunk_id}: {payload}"
        )

    if not sct.verify_token(payload, signing_key_env=signing_key_env):
        return REFUSAL_EXIT, (
            f"chunk_sequence_gate: REFUSED prior-token for next-chunk="
            f"{next_chunk_id}: HMAC verification failed under "
            f"{signing_key_env}; check EVIDENCE_SIGNING_KEY is set to "
            f"the same key used by tools/sign_chunk_token.py sign."
        )

    if check_current_head:
        try:
            r = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo,
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            return REFUSAL_EXIT, (
                f"chunk_sequence_gate: REFUSED next-chunk={next_chunk_id}: "
                f"git rev-parse HEAD failed: {e}"
            )
        head_sha = r.stdout.strip()
        token_sha = payload.get("chunk_commit_sha", "")
        if token_sha != head_sha:
            return REFUSAL_EXIT, (
                f"chunk_sequence_gate: REFUSED next-chunk={next_chunk_id}: "
                f"prior chunk token chunk_commit_sha={token_sha} != "
                f"HEAD^{{commit}}={head_sha}; binding broken."
            )

    cid = payload.get("chunk_id")
    sha_short = (payload.get("chunk_commit_sha") or "")[:7]
    return 0, (
        f"chunk_sequence_gate: OK next-chunk={next_chunk_id} "
        f"prior-token verifies (chunk_id={cid!r} "
        f"commit_sha={sha_short}…)"
    )


def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="chunk_sequence_gate",
        description="Refuses chunk-N+1 from starting when chunk-N's token does not verify (§20 / PRD §11 Phase 5 #3).",
    )
    p.add_argument(
        "--prior-token",
        required=True,
        help=f"Path to {TOKENS_ROOT}/chunk-N.token.json (or any token path).",
    )
    p.add_argument(
        "--next-chunk-id",
        required=True,
        help="The chunk-id the gate is being checked FOR (informational; helps the refusal log).",
    )
    p.add_argument("--signing-key-env", default="EVIDENCE_SIGNING_KEY")
    p.add_argument(
        "--check-current-head",
        action="store_true",
        help="Also assert token chunk_commit_sha == `git rev-parse HEAD` of --repo.",
    )
    p.add_argument("--repo", default=".", help="Repo path for --check-current-head.")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_argparser().parse_args(argv)
    code, msg = check_gate(
        prior_token_path=args.prior_token,
        next_chunk_id=args.next_chunk_id,
        signing_key_env=args.signing_key_env,
        check_current_head=args.check_current_head,
        repo=args.repo,
    )
    stream = sys.stdout if code == 0 else sys.stderr
    print(msg, file=stream)
    return code


if __name__ == "__main__":
    sys.exit(main())

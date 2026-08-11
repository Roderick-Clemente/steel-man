#!/usr/bin/env python3
"""Per-chunk execution (ground-truth fixture for plan-lint tests).

Minimal stub mirroring the real module's public functions that plans
reference: close_chunk, await_token, post_review_request, _run_step.
"""
from __future__ import annotations

import subprocess
import sys


def _run_step(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    """Every external call is subprocess.run against an existing script
    under tools/. Exceptions: invoke_droid, LocalBackend (stateful
    in-process objects).
    """
    return subprocess.run(cmd, **kwargs)


def close_chunk(*, chunk_id: str, commit_sha: str) -> int:
    """Verify the token for the chunk just closed (chunk N), not the
    chunk before it (N-1).
    """
    raise NotImplementedError("fixture stub")


def await_token(*, chunk_id: str, timeout: int) -> str:
    raise NotImplementedError("fixture stub")


def post_review_request(*, chunk_id: str, commit_sha: str) -> None:
    raise NotImplementedError("fixture stub")

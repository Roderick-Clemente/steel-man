#!/usr/bin/env python3
"""Sequence gate (ground-truth fixture for plan-lint tests).

Minimal stub mirroring the real tool's argparse surface.
"""
from __future__ import annotations

import argparse
import sys


def check_gate(
    *,
    prior_token_path: str,
    next_chunk_id: str,
    signing_key_env: str = "EVIDENCE_SIGNING_KEY",
    check_current_head: bool = False,
    repo: str = ".",
) -> tuple[int, str]:
    raise NotImplementedError("fixture stub")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--prior-token", required=True)
    p.add_argument("--next-chunk-id", required=True)
    p.add_argument("--signing-key-env", default="EVIDENCE_SIGNING_KEY")
    p.add_argument("--check-current-head", action="store_true")
    p.add_argument("--repo", default=".")
    return 0

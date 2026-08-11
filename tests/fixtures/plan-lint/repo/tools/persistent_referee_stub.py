#!/usr/bin/env python3
"""Persistent referee stub (ground-truth fixture for plan-lint tests).

Minimal stub mirroring the real tool's argparse surface + build_signed_token.
"""
from __future__ import annotations

import argparse
import sys


def build_signed_token(*, chunk_id: str, token_dir: str, reviewer_label: str = "referee-stub") -> dict:
    raise NotImplementedError("fixture stub")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--steer", required=True)
    p.add_argument("--token-dir", required=True)
    p.add_argument("--reviewer-label", default="referee-stub")
    p.add_argument("--interval", type=int, default=5)
    p.add_argument("--once", action="store_true")
    p.add_argument("--poll", action="store_true")
    return 0

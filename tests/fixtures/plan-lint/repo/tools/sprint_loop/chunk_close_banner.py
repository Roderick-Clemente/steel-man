#!/usr/bin/env python3
"""Chunk close banner (ground-truth fixture for plan-lint tests).

Minimal stub mirroring the real tool's argparse surface.
"""
from __future__ import annotations

import argparse
import sys


def render(*, token_path: str, signing_key_env: str = "EVIDENCE_SIGNING_KEY") -> str:
    raise NotImplementedError("fixture stub")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--token-path", required=True)
    p.add_argument("--signing-key-env", default="EVIDENCE_SIGNING_KEY")
    p.add_argument("--plan-review-rendered", action="store_true")
    p.add_argument("--validation-gate-executed", action="store_true")
    return 0

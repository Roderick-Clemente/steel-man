#!/usr/bin/env python3
"""Cross-family review gate (ground-truth fixture for plan-lint tests).

Minimal stub mirroring the real tool's public API: check_reviewer_panel
signature, family_of, ACCEPT_CLASS.
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Any

_TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

from sprint_loop.config import MODEL_FAMILY_MAP  # noqa: E402
import sign_chunk_token as sct  # noqa: E402

ACCEPT_CLASS: frozenset[str] = sct.ACCEPT_CLASS


def family_of(model_id: str) -> tuple[str, str]:
    if model_id in MODEL_FAMILY_MAP:
        return MODEL_FAMILY_MAP[model_id]
    return ("unknown", "unknown")


def check_reviewer_panel(
    *,
    implementer_model_id: str,
    reviewer_model_ids: list[str],
    reviewer_verdicts: list[str],
    reviewer_envelope_sha256s: list[str],
) -> list[Any]:
    """Pure refusal-list producer. Returns list of RefusalLog-like objects."""
    raise NotImplementedError("fixture stub")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--implementer-model-id", required=True)
    p.add_argument("--reviewer-models", required=True)
    p.add_argument("--reviewers-verdicts-json", required=True)
    p.add_argument("--reviewers-envelope-sha256s", required=True)
    p.add_argument("--token-dir", required=True)
    p.add_argument("--chunk-id", required=True)
    p.add_argument("--signed-by", default="cross-family-review")
    p.add_argument("--signing-key-env", default="EVIDENCE_SIGNING_KEY")
    return 0

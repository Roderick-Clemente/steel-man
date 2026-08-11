#!/usr/bin/env python3
"""Sign and verify chunk-close tokens (ground-truth fixture for plan-lint tests).

Minimal stub mirroring the real tool's public API surface that plans
reference: ACCEPT_CLASS, REVIEWER_REQUIRED_KEYS, build_token signature.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from typing import Any

TOKEN_SCHEMA = "chunk-token/v1"

ACCEPT_CLASS: frozenset[str] = frozenset({"ACCEPT", "ACCEPT-WITH-NITS"})

REVIEWER_REQUIRED_KEYS: tuple[str, ...] = (
    "family", "model_id", "verdict", "envelope_sha256",
)


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
    raise NotImplementedError("fixture stub")


def verify_token(token: Any, *, signing_key_env: str = "EVIDENCE_SIGNING_KEY") -> bool:
    raise NotImplementedError("fixture stub")

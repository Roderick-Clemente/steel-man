#!/usr/bin/env python3
"""Operator-eye visual signal at chunk close.

Per PRD §11 Phase 5 deliverable #5:
  * ✅ when chunk-N.token.json's HMAC verifies under EVIDENCE_SIGNING_KEY
  * ⛔ when token.json is missing OR signature invalid

ABSENCE ≠ skill exhausted. ABSENCE is a runtime contract violation with
a recoverable path (PRD §11 Phase 5 §5 troubleshooting checklist). The
signal is ENFORCEMENT at the operator-eye layer: presence =
runtime check passed; absence = runtime check failed or never ran.

Composition: composes ``sign_chunk_token.verify_token`` to bind the
emoji output to the actual HMAC verification result. No decoration
without verifiable state.

The companion full signature 🤺👀✅⛔ is the project's four-tone visual
signal. This module owns the ✅/⛔ half (chunk-close half). The
🤺/👀 halves (plan-review/validation-gate halves) are owned by other
adapter points; if you wire a new one, mirror the same
"verify-then-emit" gate so emojis cannot render without a verified
condition behind them.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

_TOOLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

import sign_chunk_token as sct  # noqa: E402


CHECKLIST_POINTER = (
    "Operator-eye troubleshooting checklist for absent signal "
    "(PRD §11 Phase 5 §5):\n"
    "  1. Read phase-4.5/tokens/chunk-N.token.json. If absent:\n"
    "     cross_family_review.py refused.\n"
    "  2. Verify signature. If signature bad: EVIDENCE_SIGNING_KEY\n"
    "     mismatch. Check tools/run-with-model.sh for the key it\n"
    "     signs with; set the same key at verify time.\n"
    "  3. Run tools/chunk_sequence_gate.py --prior-token <path>\n"
    "     --next-chunk-id N+1. Exit 6 means the prior chunk's\n"
    "     token still doesn't verify; roll back.\n"
    "  4. Check telemetry/runs.jsonl for the chunk's run_id.\n"
    "  5. Inspect phase-4.5/build-evidence/<run-id>/<RUN_STATE>.json\n"
    "     for the last-known step prior to the gap.\n"
    "  6. Refresh tools/install-skill.sh — the canonical skill\n"
    "     may not have been loaded into the agent's session context."
)


def render(token_path: str | None, *, signing_key_env: str = "EVIDENCE_SIGNING_KEY",
           checklist_path: str | None = None,
           plan_review_rendered: bool = False,
           validation_gate_executed: bool = False) -> tuple[str, str]:
    """Return (stdout_line, stderr_text).

    stdout_line: the single-line chunk-close signal.
    stderr_text: empty on success; checklist pointer on refusal, so the
      signal path remains one printable line on stdout and the operator
      has the checklist nearby on stderr.
    """
    plan_emoji = "🤺" if plan_review_rendered else "(plan-review-not-rendered)"
    val_emoji = "👀" if validation_gate_executed else "(validation-gate-not-executed)"

    if not token_path or not os.path.exists(token_path):
        line = f"{plan_emoji} {val_emoji} ⛔ (token missing) chunk-close BANNER ⛔"
        return line, CHECKLIST_POINTER

    try:
        with open(token_path) as f:
            token = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        line = f"{plan_emoji} {val_emoji} ⛔ (token read failed) chunk-close BANNER ⛔"
        err = f"chunk_close_banner: cannot read {token_path}: {e}\n{CHECKLIST_POINTER}"
        return line, err

    if sct.verify_token(token, signing_key_env=signing_key_env):
        sha = token.get("chunk_commit_sha", "")[:7] or "<no-sha>"
        chunk_id = token.get("chunk_id", "<no-chunk-id>")
        line = f"{plan_emoji} {val_emoji} ✅ chunk-close BANNER chunk={chunk_id} sha={sha}…"
        return line, ""
    line = f"{plan_emoji} {val_emoji} ⛔ (token HMAC fails) chunk-close BANNER ⛔"
    return line, CHECKLIST_POINTER


def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="chunk_close_banner",
        description="Operator-eye visual signal at chunk close (PRD §11 Phase 5 #5).",
    )
    p.add_argument("--token-path", default="",
                   help="Path to phase-4.5/tokens/chunk-N.token.json")
    p.add_argument("--signing-key-env", default="EVIDENCE_SIGNING_KEY")
    p.add_argument("--plan-review-rendered", action="store_true",
                   help="Emit 🤺 for the adversarial-plan-render half of the four-tone signature.")
    p.add_argument("--validation-gate-executed", action="store_true",
                   help="Emit 👀 for the validation-gate-executed half.")
    p.add_argument("--checklist-to-stderr", action="store_true",
                   help="(default: always on refusal; ignored on accept) Keep checklist pointer "
                        "on stderr.")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_argparser().parse_args(argv)
    line, err = render(
        args.token_path or None,
        signing_key_env=args.signing_key_env,
        plan_review_rendered=args.plan_review_rendered,
        validation_gate_executed=args.validation_gate_executed,
    )
    print(line)
    if err:
        print(err, file=sys.stderr)
        # Exit code is bound to the verification result, not to the emoji.
        # The emoji is the display of enforcement; the exit code IS enforcement.
        return 6
    return 0


if __name__ == "__main__":
    sys.exit(main())

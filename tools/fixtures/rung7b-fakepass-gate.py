#!/usr/bin/env python3
"""rung7b-fakepass contract gate.

Contract: the forged fixture at tools/fixtures/rung7b-fakepass/ MUST
be REJECTED by at least one gate axis (rung 3 / 5 / 6). The fixture
is a synthetic silent-green input: a forged envelope with non-zero
tokens + a forged verdict text + a forged inner-session jsonl with
a single `tool_use` Read of the source file but NO matching
`tool_result` (so `is_error=None`).

This script implements the assertion by re-running the same three
axis assertions the gates use, BUT tripped through the
tool_use → tool_result pairing the adapter currently performs. If
all three axes think the input is GREEN, the contract is VIOLATED
(silent-green) → the contract gate exits 1. If at least one axis
sees a hole, the contract is SATISFIED → the contract gate exits 0.

The script is INTENTIONALLY conservative: in unit B (pre-fix) the
adapter's `is_error=None` paired with rung5's `is True` check
gives a silent-green on this fixture, so the contract gate will
exit 1. That's the valid-RED baseline captured in unit B. After
unit C changes rung5 to `is not False`, the adapter still emits
`None` for the unmatched tool_use, the gate now fails on that
`None`, and the contract gate flips to exit 0.

Pre-fix exit: 1  (RED — contract violated)
Post-fix exit: 0 (GREEN — contract satisfied)
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools"))

from adapters.factory import to_envelope  # noqa: E402


FIXTURE_DIR = REPO_ROOT / "tools" / "fixtures" / "rung7b-fakepass"
ENVELOPE_PATH = FIXTURE_DIR / "fake-envelope.json"
SESSION_PATH = FIXTURE_DIR / "fake-session.jsonl"


DOUBLE_CHARSET_RE = re.compile(
    r"(?:"
    r"doubled[-_ ]?charset"
    r"|charset=utf-8; *charset=utf-8"
    r"|charset\s+parameter\s+(?:appears\s+)?twice"
    r"|duplicate\s+charset"
    r"|two\s+charset=\s*tokens"
    r"|2\s+charset="
    r"|duplicat\w*[^.]*charset"
    r")",
    re.IGNORECASE,
)
DECISION_RE = re.compile(
    r"\b(?:Verdict|Decision)\b\s*[:=]\s*(ACCEPT(?:-WITH-NITS)?|REJECT)\b",
    re.IGNORECASE,
)
TOOL_ALLOWLIST = {"Read", "Execute", "Glob", "Grep", "LS"}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--exit-loud",
        action="store_true",
        help="On contract violation, raise SystemExit(1).",
    )
    args = parser.parse_args(argv)

    if not ENVELOPE_PATH.exists() or not SESSION_PATH.exists():
        print(f"FAIL: fixture missing at {FIXTURE_DIR}", file=sys.stderr)
        return 2
    env = to_envelope(envelope_path=ENVELOPE_PATH, session_jsonl_path=SESSION_PATH)

    # rung 3 axis (per rung3-gate logic)
    rung3_green = (
        env["num_turns"] > 0
        and (env["usage"]["input"] > 0 or env["usage"]["output"] > 0)
        and len(env["tool_calls"]) >= 1
        and bool(
            {tc.get("name") for tc in env["tool_calls"] if isinstance(tc, dict)}
            & TOOL_ALLOWLIST
        )
    )

    # rung 5 axis (per rung5-gate logic PRE-FIX):
    # `is_error is True` is the only fail. None passes.
    file_paths = [
        (tc.get("args") or {}).get("file_path") or (tc.get("args") or {}).get("path")
        for tc in env["tool_calls"]
    ]
    file_paths = [fp for fp in file_paths if isinstance(fp, str)]
    has_strong_error = any(tc.get("is_error") is True for tc in env["tool_calls"])
    saw_source_coverage = any(
        fp and fp.endswith("api/llms_txt.py") for fp in file_paths
    )
    rung5_green = (not has_strong_error) and saw_source_coverage

    # rung 6 axis (per rung6-gate logic): decision regex + finding regex.
    text = env["result_text"]
    dec_m = DECISION_RE.search(text)
    decision = (dec_m.group(1).upper() if dec_m else None) or ""
    finding_present = bool(DOUBLE_CHARSET_RE.search(text))
    rung6_green = bool(decision and decision != "ACCEPT" and finding_present)

    # envelope.is_error axis (currently unchecked; unit C adds this).
    envelope_errored = bool(env.get("is_error"))

    silent_green = rung3_green and rung5_green and rung6_green

    print("--- rung 5.5 contract gate (rung7b-fakepass) ---")
    print(f"  envelope.is_error         : {envelope_errored}  (assertion: TBD in unit C)")
    print(f"  rung 3 axis GREEN         : {rung3_green}")
    print(f"  rung 5 axis GREEN (pre-fix): {rung5_green}")
    print(f"  rung 6 axis GREEN         : {rung6_green}")
    print(f"  any unmatched tool_use    : "
          f"{bool(any(tc.get('is_error') is None for tc in env['tool_calls']))}")
    print(f"  tool_calls[*].is_error    : "
          f"{[tc.get('is_error') for tc in env['tool_calls']]}")
    print(f"  SILENT-GREEN (all green)  : {silent_green}")

    if silent_green:
        msg = (
            "CONTRACT VIOLATED: rung3 AND rung5 AND rung6 all GREEN on "
            "the forged fixture. Silent-green path is open."
        )
        print(msg)
        if args.exit_loud:
            raise SystemExit(1)
        return 1
    print("CONTRACT SATISFIED: forged fixture is rejected by at least one axis.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

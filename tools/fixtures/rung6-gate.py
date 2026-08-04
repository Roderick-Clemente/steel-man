#!/usr/bin/env python3
"""Rung 6 gate — assert the INVARIANT outcome of the validator's verdict.

Brief: "assert the INVARIANT outcome — decision ≠ ACCEPT AND a
normalized 'doubled charset' finding is present — NOT verbatim wording.
Gate: reproduces the known 4-family verdict (ACCEPT-WITH-NITS + blind
charset catch)."

This script reads the rung-3 envelope's `result` text and asserts:
1. The verdict decision is one of {ACCEPT, ACCEPT-WITH-NITS, REJECT}.
2. The decision is NOT "ACCEPT" (so ACCEPT-WITH-NITS or REJECT both OK).
3. A normalized 'doubled charset' mention exists somewhere in the
   verdict text — across recognized phrasings.

Exits 0 on green, SystemExit(1) with --exit-loud on FAIL.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


# Decision header — accepts "Verdict: REJECT", "verdict: ACCEPT-WITH-NITS",
# "Decision = ACCEPT", "VERDICT: REJECT", etc.
DECISION_RE = re.compile(
    r"\b(?:Verdict|Decision)\b\s*[:=]\s*(ACCEPT(?:-WITH-NITS)?|REJECT)\b",
    re.IGNORECASE,
)

# Normalized "doubled charset" mentions — many phrasings, accept any.
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


def decision(text: str) -> str | None:
    m = DECISION_RE.search(text)
    return m.group(1).upper() if m else None


def has_double_charset_finding(text: str) -> bool:
    return bool(DOUBLE_CHARSET_RE.search(text))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--exit-loud",
        action="store_true",
        help="On FAIL, raise SystemExit(1).",
    )
    parser.add_argument(
        "--envelope",
        required=True,
        type=Path,
        help="The rung-3 envelope (used to recover the verdict text).",
    )
    parser.add_argument(
        "--allow-accept",
        action="store_true",
        help="RELAX: allow ACCEPT (used only for fixture tests of the gate itself).",
    )
    args = parser.parse_args(argv)

    if not args.envelope.exists():
        print(f"FAIL: envelope missing: {args.envelope}", file=sys.stderr)
        return 2
    envelope = json.loads(args.envelope.read_text())
    text = envelope.get("result", "") or ""
    if not text:
        print("FAIL: envelope has empty `result` text", file=sys.stderr)
        return 2

    print("verdict text first 240 chars:")
    print(text[:240])
    print("---")

    dec = decision(text)
    has_finding = has_double_charset_finding(text)

    fails: list[str] = []
    if not dec:
        fails.append("no recognized Verdict/Decision line in text")
    elif dec == "ACCEPT" and not args.allow_accept:
        fails.append("decision equals ACCEPT (only ACCEPT-WITH-NITS or REJECT allowed)")
    if not has_finding:
        fails.append(
            "no normalized 'doubled charset' mention in verdict text; "
            "expected a doubled-charset phrasing. The validator may have "
            "fabricated its claim from KB without inspecting the source."
        )

    if fails:
        print()
        print("RED — rung 6 gate failed:")
        for f in fails:
            print(f"  - {f}")
        if args.exit_loud:
            raise SystemExit(1)
        return 1

    print()
    print(
        "GREEN — rung 6 gate: decision %r + doubled-charset finding present." % dec
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

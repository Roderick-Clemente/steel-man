#!/usr/bin/env python3
"""Rung 6 gate (refactored) — assert the INVARIANT outcome of the verifier's verdict.

Brief: "assert the INVARIANT outcome — decision ≠ ACCEPT AND a
normalized 'doubled charset' finding is present — NOT verbatim wording."

After the seam refactor (commit ahead), this gate consumes the
NORMALIZED envelope's `result_text` field via
`tools/adapters/factory.to_envelope`. It does NOT read Factory's
envelope.result directly. The decision regex and the doubled-charset
finding regex are unchanged; only where the text comes from is
behind the adapter.

Behavior preservation is asserted by running this gate before/after
the refactor on the same envelope. Same GREEN/RED verdict on
identical input.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools"))

from adapters.factory import to_envelope  # noqa: E402


DECISION_RE = re.compile(
    r"\b(?:Verdict|Decision)\b\s*[:=]\s*(ACCEPT(?:-WITH-NITS)?|REJECT)\b",
    re.IGNORECASE,
)

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
        "--envelope",
        required=True,
        type=Path,
        help="Path to the raw droid exec envelope.",
    )
    parser.add_argument(
        "--session-jsonl",
        type=Path,
        default=None,
        help="Path to the inner-session jsonl (not used for rung-6 logic; consumed via adapter if present).",
    )
    parser.add_argument(
        "--allow-accept",
        action="store_true",
        help="RELAX: allow ACCEPT (used only for fixture tests of the gate itself).",
    )
    parser.add_argument(
        "--exit-loud",
        action="store_true",
        help="On FAIL, raise SystemExit(1).",
    )
    args = parser.parse_args(argv)

    env = to_envelope(
        envelope_path=args.envelope,
        session_jsonl_path=args.session_jsonl,
    )
    text = env["result_text"]
    if not text:
        print("FAIL: normalised envelope has empty result_text", file=sys.stderr)
        return 2

    print("verdict text first 240 chars:")
    print(env["result_text_first_240chars"])
    print("---")

    dec = decision(text)
    has_finding = has_double_charset_finding(text)

    # envelope.is_error gate here too: aborted runs must not mint
    # GREEN regardless of whether prose happens to parse.
    if env.get("is_error"):
        print(
            "envelope.is_error=True; the run itself aborted "
            f"(envelope session_id={env.get('session_id')!r}). Gate refuses "
            "to mint GREEN on an aborted run regardless of tools/prose."
        )
        if args.exit_loud:
            raise SystemExit(1)
        return 1

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

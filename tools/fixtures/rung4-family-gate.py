#!/usr/bin/env python3
"""Rung 4 gate — family-verification.

Brief: "parse the effective provider/model/family from run metadata for
the seat. HARD-FAIL if the validator's family == the executor's family,
on silent fallback, or on unknown family. Gate: feed a deliberately
same-family model and confirm it REFUSES. The router drives the loop;
it must NEVER override a seat's pin."

This script:
1. Loads tools/fixtures/rung4-family-decisions.json (resolver outputs)
2. Asserts validator_family != executor_family for the LIVE state.
3. Asserts neither family is unknown and silent-fallback proxy is False.
4. Returns ALLOW for LIVE state.
5. NEGATIVE CONTROL: feeds the gate function same-family and unknown
   inputs and confirms the gate REFUSES those (with assertion).

Exits 0 on green, SystemExit(1) on FAIL with --exit-loud.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DECISIONS_PATH = REPO_ROOT / "tools" / "fixtures" / "rung4-family-decisions.json"


def family_check(validator_family: str, executor_family: str) -> tuple[str, str]:
    """Decide ALLOW/REFUSE based on family comparison.

    Returns (decision, reason).
    """
    if not validator_family or validator_family == "unknown":
        return "REFUSE", f"validator family is '{validator_family}' (unknown)"
    if not executor_family or executor_family == "unknown":
        return "REFUSE", f"executor family is '{executor_family}' (unknown)"
    if validator_family == executor_family:
        return "REFUSE", (
            f"validator family '{validator_family}' equals executor "
            f"family '{executor_family}' — same-family collapse forbidden"
        )
    return "ALLOW", (
        f"validator family '{validator_family}' != executor "
        f"family '{executor_family}'"
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--exit-loud",
        action="store_true",
        help="On FAIL, raise SystemExit(1).",
    )
    args = parser.parse_args(argv)

    if not DECISIONS_PATH.exists():
        print(f"FAIL: decisions missing: {DECISIONS_PATH}", file=sys.stderr)
        return 2
    decisions = json.loads(DECISIONS_PATH.read_text())

    print("=" * 60)
    print("LIVE state — rung 4")
    print("=" * 60)
    validator_family = decisions["validator_seat"]["family"]
    executor_family = decisions["executor_seat"]["family"]
    print(f"  validator family : {validator_family!r}")
    print(f"  executor family  : {executor_family!r}")

    decision, reason = family_check(validator_family, executor_family)
    print(f"  family-gate     : {decision} ({reason})")

    # Unknown family / silent-fallback proxy assertions.
    silent_fallback_proxy = decisions["result"].get("executor_uses_silent_fallback_proxy")
    executor_unknown = decisions["result"].get("executor_unknown_family")
    fails: list[str] = []
    if silent_fallback_proxy:
        fails.append("executor_uses_silent_fallback_proxy=True (silent fallback on the auto-router)")
    if executor_unknown:
        fails.append("executor_unknown_family=True")
    if decision != "ALLOW":
        fails.append(f"LIVE family-gate returned {decision!r} (must be ALLOW in production)")

    # Negative controls: gate must REFUSE same-family and unknown inputs.
    print()
    print("=" * 60)
    print("Negative controls — same-family, unknown, silent-proxy")
    print("=" * 60)
    neg_cases = [
        ("openai", "openai", "REFUSE"),
        ("fireworks", "fireworks", "REFUSE"),
        ("anthropic", "anthropic", "REFUSE"),
        ("openai", "fireworks", "ALLOW"),  # this is the LIVE state
        ("fireworks", "openai", "ALLOW"),  # inverse
        ("unknown", "fireworks", "REFUSE"),
        ("fireworks", "unknown", "REFUSE"),
        ("", "fireworks", "REFUSE"),
    ]
    for vf, ef, expected in neg_cases:
        d, r = family_check(vf, ef)
        mark = "ok" if d == expected else "FAIL"
        print(f"  [{mark}] family_check({vf!r:14s}, {ef!r:14s}) -> {d!r}  (expected {expected!r})  reason={r}")
        if d != expected:
            fails.append(
                f"family_check({vf!r}, {ef!r}) returned {d!r}, expected {expected!r}"
            )

    if fails:
        print()
        print("RED: rung 4 gate failed; details:")
        for f in fails:
            print(f"  - {f}")
        if args.exit_loud:
            raise SystemExit(1)
        return 1

    print()
    print("GREEN: rung 4 family-gate.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

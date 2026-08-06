#!/usr/bin/env python3
"""Run a locked test and classify whether the observed RED is valid.

A valid RED means the test collected, executed the intended path, reached its
assertion, and failed because the required behavior is absent or wrong. Syntax
errors, import errors, missing fixtures, tautologies, weak truthiness, and
failures for unrelated reasons are invalid RED.

Usage:
    python3 phase-1/scripts/valid-red.py --pilot-root <path> \
        --test-file <path> --accepted-assertion <phrase> [-o json]
"""
import argparse
import json
import re
import subprocess
import sys
from typing import Tuple


# Invalid-RED signatures we can detect from pytest output. Each tuple is
# (regex, reason). A match makes the RED invalid regardless of the intended
# assertion.
INVALID_RED_SIGNATURES = [
    (r"SyntaxError:", "syntax error"),
    (r"IndentationError:", "indentation error"),
    (r"ModuleNotFoundError:", "missing module import"),
    (r"ImportError:", "import error"),
    (r"FixtureLookupError:", "missing fixture"),
    (r"conftest\.py", "conftest error"),
    (r"collection error", "test collection error"),
    (r"INTERNAL ERROR", "pytest internal error"),
    (r"assert\s+True\b", "tautological assertion"),
    (r"assert\s+1\s*==\s*1\b", "tautological assertion"),
    (r"assert\s+0\s*==\s*0\b", "tautological assertion"),
    (r"MagicMock\(.*\)\s*is\s*not\s*None", "assertion on subject mock"),
    (r"mock\s*=\s*MagicMock", "subject under test mocked"),
    # Class 4 — environment rejection (PRD §5.4: empty selection, unavailable services).
    (r"collected\s+0\s+items|no tests? ran|test selection empty", "empty test selection"),
    (r"unavailable|service.*unavailable|connection.*refused|could not connect to", "service unavailable"),
]


def run_pytest(pilot_root: str, test_file: str, python: str) -> Tuple[int, str, str]:
    cmd = [python, "-m", "pytest", test_file, "-v"]
    result = subprocess.run(
        cmd,
        cwd=pilot_root,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return result.returncode, result.stdout, result.stderr


def classify(exit_code: int, stdout: str, stderr: str, accepted_assertion: str) -> dict:
    combined = f"{stdout}\n{stderr}"

    # 1. A passing test is not a RED.
    if exit_code == 0 and "passed" in combined.lower():
        return {
            "valid": False,
            "reason": "Invalid RED: test passed (no failure to fix)",
            "exit_code": exit_code,
        }

    # 2. Reject known bad-RED signatures.
    for pattern, reason in INVALID_RED_SIGNATURES:
        if re.search(pattern, combined, re.IGNORECASE):
            return {
                "valid": False,
                "reason": f"Invalid RED: {reason}",
                "exit_code": exit_code,
            }

    # 3. A pytest failure must actually have occurred.
    if exit_code == 0:
        return {
            "valid": False,
            "reason": "Invalid RED: pytest exited 0 with no failure",
            "exit_code": exit_code,
        }
    if "FAILED" not in combined and "failures" not in combined.lower():
        return {
            "valid": False,
            "reason": "Invalid RED: no pytest failure recorded",
            "exit_code": exit_code,
        }

    # 4. The failure must relate to the accepted assertion. We do a
    # case-insensitive substring match on the combined output; the assertion
    # phrase should appear in the failure report or in the assertion message.
    assertion_phrase = accepted_assertion.lower()
    if assertion_phrase not in combined.lower():
        return {
            "valid": False,
            "reason": "Invalid RED: failure does not match accepted assertion",
            "exit_code": exit_code,
        }

    return {
        "valid": True,
        "reason": "Valid RED: intended assertion ran and failed",
        "exit_code": exit_code,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify a RED run.")
    parser.add_argument("--pilot-root", required=True, help="Path to the pilot repo root.")
    parser.add_argument("--test-file", required=True, help="Test file path relative to pilot root.")
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python interpreter to run pytest (default: the interpreter running this script).",
    )
    parser.add_argument(
        "--accepted-assertion",
        required=True,
        help="Phrase that must appear in the failure for the RED to be valid.",
    )
    parser.add_argument(
        "-o",
        "--output",
        choices=["text", "json"],
        default="text",
        help="Output format.",
    )
    args = parser.parse_args()

    try:
        exit_code, stdout, stderr = run_pytest(args.pilot_root, args.test_file, args.python)
    except subprocess.TimeoutExpired:
        result = {
            "valid": False,
            "reason": "Invalid RED: pytest timed out",
            "exit_code": -1,
            "stdout": "",
            "stderr": "",
        }
        print(json.dumps(result) if args.output == "json" else "RED REFUSED: pytest timed out")
        return 1

    classification = classify(exit_code, stdout, stderr, args.accepted_assertion)
    classification["stdout"] = stdout
    classification["stderr"] = stderr

    if args.output == "json":
        print(json.dumps(classification, indent=2))
    else:
        status = "VALID RED" if classification["valid"] else "INVALID RED"
        print(f"{status}: {classification['reason']}")
        print(f"pytest exit_code: {exit_code}")

    return 0 if classification["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())

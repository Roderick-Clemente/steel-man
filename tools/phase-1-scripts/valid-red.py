#!/usr/bin/env python3
"""Run a locked test and classify whether the observed RED is valid.

A valid RED means the test collected, executed the intended path, reached its
assertion, and failed because the required behavior is absent or wrong. Syntax
errors, import errors, missing fixtures, tautologies, weak truthiness, and
failures for unrelated reasons are invalid RED.

Classification reads pytest's *structural* evidence first — collected count,
collection ERROR versus executed FAILURES, exit code — and applies text
signatures only in the region where each one means what it says. A test that
imports a not-yet-existing module inside a guard and quotes the cause in its
assertion message is a valid RED, not an import failure.

Usage:
    python3 phase-1/scripts/valid-red.py --pilot-root <path> \
        --test-file <path> --accepted-assertion <phrase> [-o json]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys

# Regex to strip ANSI color escape codes from pytest output. Without this,
# patterns like `assert\s+True` fail to match because pytest inserts escape
# codes between tokens (e.g. \x1b[94massert\x1b[39;49;00m \x1b[94mTrue).
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    """Remove ANSI color escape codes from text."""
    return _ANSI_RE.sub("", text)


# Invalid-RED signatures we can detect from pytest output. Each tuple is
# (regex, reason).
#
# The list is split by *where in the output a match is meaningful*, because
# matching the whole stdout+stderr blob cannot tell "the test file failed to
# import" from "the test executed, reached its assertion, and the assertion
# message quotes an import error". A well-written RED for a not-yet-existing
# module does the latter, and the undivided list rejected it — penalising the
# test for explaining itself.
#
# COLLECTION_PHASE_SIGNATURES describe a file that never ran. They are only
# consulted once the structural evidence (collected count, ERRORS section, exit
# code, presence of executed failures) already shows a collection/execution
# failure, or when they match outside the FAILURES region.
COLLECTION_PHASE_SIGNATURES = [
    (r"SyntaxError:", "syntax error"),
    (r"IndentationError:", "indentation error"),
    (r"ModuleNotFoundError:", "missing module import"),
    (r"ImportError:", "import error"),
    (r"FixtureLookupError:", "missing fixture"),
    (r"conftest\.py", "conftest error"),
    (r"collection error", "test collection error"),
    (r"INTERNAL ERROR", "pytest internal error"),
    # Class 4 — environment rejection (PRD §5.4: empty selection).
    (r"collected\s+0\s+items|no tests? ran|test selection empty", "empty test selection"),
]

# TEST_QUALITY_SIGNATURES describe a test that ran but asserts nothing real.
# They still invalidate an executed failure, scoped to the assertion lines and
# displayed test source inside the FAILURES region so that a traceback which
# merely renders such a line in unrelated context does not trip them.
TEST_QUALITY_SIGNATURES = [
    (r"assert\s+True\b", "tautological assertion"),
    (r"assert\s+1\s*==\s*1\b", "tautological assertion"),
    (r"assert\s+0\s*==\s*0\b", "tautological assertion"),
    (r"MagicMock\(.*\)\s*is\s*not\s*None", "assertion on subject mock"),
    (r"mock\s*=\s*MagicMock", "subject under test mocked"),
]

# ENVIRONMENT_SIGNATURES — class 4 environment rejection, unchanged from the
# undivided list: matched against the whole output regardless of structure.
ENVIRONMENT_SIGNATURES = [
    (
        r"unavailable|service.*unavailable|connection.*refused|could not connect to",
        "service unavailable",
    ),
]

# pytest section banners, e.g. `======= FAILURES =======`.
_BANNER_RE = re.compile(r"^=+ (.*?) =+$", re.MULTILINE)


def pytest_sections(text: str) -> list[tuple[str, str]]:
    """Split pytest output into ``(section title, section body)`` pairs."""
    banners = list(_BANNER_RE.finditer(text))
    sections = []
    for index, banner in enumerate(banners):
        end = banners[index + 1].start() if index + 1 < len(banners) else len(text)
        sections.append((banner.group(1).strip(), text[banner.end() : end]))
    return sections


def failures_region(text: str) -> str:
    """Return the body of the FAILURES section(s) — evidence tests executed."""
    return "\n".join(body for title, body in pytest_sections(text) if title == "FAILURES")


def collection_error_region(text: str) -> str:
    """Return the ERRORS section(s) plus any ``ERROR ...`` short-summary lines."""
    parts = []
    for title, body in pytest_sections(text):
        if title == "ERRORS":
            parts.append(body)
        elif title.lower().startswith("short test summary"):
            parts.extend(
                line for line in body.splitlines() if re.match(r"\s*ERROR\b", line)
            )
    return "\n".join(parts)


def outside_failures_region(text: str) -> str:
    """Return collection-relevant output, excluding failures and warnings.

    Pytest's warnings summary routinely names source files such as
    ``tests/conftest.py``. That is not collection evidence, so it must not
    trigger a collection-phase signature for an otherwise executed failure.
    """
    banners = list(_BANNER_RE.finditer(text))
    head = text[: banners[0].start()] if banners else text
    parts = [head]
    parts.extend(
        body
        for title, body in pytest_sections(text)
        if title != "FAILURES" and not title.lower().startswith("warnings summary")
    )
    kept = "\n".join(parts).splitlines()
    return "\n".join(line for line in kept if not re.match(r"\s*FAILED\b", line))


def assertion_region(text: str) -> str:
    """Return the assertion evidence inside FAILURES: ``E`` lines, the failing
    statement (``>``) and the displayed test source, without locals reprs."""
    return "\n".join(
        line
        for line in failures_region(text).splitlines()
        if re.match(r"(E\s|>\s|\s{4,}\S)", line)
    )


def _first_signature(text: str, signatures: list[tuple[str, str]]) -> str | None:
    for pattern, reason in signatures:
        if re.search(pattern, text, re.IGNORECASE):
            return reason
    return None


def run_pytest(pilot_root: str, test_file: str, python: str) -> tuple[int, str, str]:
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
    # Strip ANSI color codes so regex patterns match across pytest's colored
    # output. Without this, escape codes between tokens (e.g. between
    # "assert" and "True") break whitespace-based patterns.
    combined = strip_ansi(f"{stdout}\n{stderr}")

    # 1. A passing test is not a RED.
    if exit_code == 0 and "passed" in combined.lower():
        return {
            "valid": False,
            "reason": "Invalid RED: test passed (no failure to fix)",
            "exit_code": exit_code,
        }

    # 2. Structural evidence first. A file that genuinely cannot be imported
    # yields a collection ERROR and zero executed tests; a file that ran and
    # failed yields a FAILURES section and FAILED short-summary lines.
    counts = re.findall(r"collected\s+(\d+)\s+items?", combined, re.IGNORECASE)
    collected = int(counts[-1]) if counts else None
    collection_error = bool(
        exit_code == 2
        or collection_error_region(combined).strip()
        or re.search(r"errors? during collection", combined, re.IGNORECASE)
    )
    executed_failure = bool(failures_region(combined).strip()) or "FAILED" in combined

    # 3. Nothing ran, or it never got past collection: the collection-phase
    # signatures are the right explanation here, and only here.
    if collected == 0 or collection_error or not executed_failure:
        reason = (
            _first_signature(combined, COLLECTION_PHASE_SIGNATURES)
            or _first_signature(combined, ENVIRONMENT_SIGNATURES)
            or ("test collection error" if collection_error else "no pytest failure recorded")
        )
        return {
            "valid": False,
            "reason": f"Invalid RED: {reason}",
            "exit_code": exit_code,
        }

    # 4. Tests executed and failed. Collection-phase signatures no longer
    # invalidate on their own — but they still do when they appear outside the
    # FAILURES region, where they cannot be part of an assertion message.
    reason = (
        _first_signature(assertion_region(combined), TEST_QUALITY_SIGNATURES)
        or _first_signature(combined, ENVIRONMENT_SIGNATURES)
        or _first_signature(outside_failures_region(combined), COLLECTION_PHASE_SIGNATURES)
    )
    if reason:
        return {
            "valid": False,
            "reason": f"Invalid RED: {reason}",
            "exit_code": exit_code,
        }

    # 5. A pytest failure must actually have occurred.
    if exit_code == 0:
        return {
            "valid": False,
            "reason": "Invalid RED: pytest exited 0 with no failure",
            "exit_code": exit_code,
        }

    # 6. The failure must relate to the accepted assertion. We do a
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

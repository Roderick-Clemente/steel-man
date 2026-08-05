#!/usr/bin/env python3
"""Rung 1 grep gate.

Reads tools/fixtures/doubled-charset-pin.json, looks up the pinned head_sha
in the source repo listed in the pin, and asserts that the pinned
`api/llms_txt.py` blob actually contains the doubled-charset defect
literal. Exits 0 on PASS, exits non-zero on FAIL.

NOTE: this is the calibration rung's standalone gate — no flight rules,
no validator, no diff-render. Just: is the pinned SHA actually carrying
the defect we say it does?

Usage:
    python3 tools/fixtures/rung1-grep-gate.py --exit-loud
    # or just
    python3 tools/fixtures/rung1-grep-gate.py
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PIN_PATH = REPO_ROOT / "tools" / "fixtures" / "doubled-charset-pin.json"


def _git_show_blob(source_clone: str, head_sha: str, blob_path: str) -> str:
    out = subprocess.run(
        ["git", "show", f"{head_sha}:{blob_path}"],
        cwd=source_clone,
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--exit-loud",
        action="store_true",
        help="On FAIL, print diagnostic + exit 1 — the brief's 'silent-green is the platform default' rule.",
    )
    args = parser.parse_args(argv)

    if not PIN_PATH.exists():
        print(f"FAIL: pin not found: {PIN_PATH}", file=sys.stderr)
        return 2

    pin = json.loads(PIN_PATH.read_text())
    head_sha = pin["fixture"]["head_sha"]
    head_subject = pin["fixture"]["head_sha_subject"]
    defect_literal = pin["defect_evidence"]["defect_string_literal"]
    expected_occurrences = pin["defect_evidence"]["defect_string_literal_occurrences_at_head"]
    source_clone = pin["fixture"]["source_local_clone"]

    print(f"rung 1 grep gate: head_sha        : {head_sha}")
    print(f"                   subject         : {head_subject}")
    print(f"                   source clone    : {source_clone}")
    print(f"                   defect literal  : {defect_literal!r}")
    print(f"                   expected count  : {expected_occurrences}")

    blob = _git_show_blob(source_clone, head_sha, "api/llms_txt.py")
    actual_occurrences = blob.count(defect_literal)
    print(f"                   actual  count  : {actual_occurrences}")

    if actual_occurrences != expected_occurrences:
        msg = (
            f"RED: head={head_sha} defect literal appears {actual_occurrences} "
            f"times, pin said {expected_occurrences}. Pin is stale; re-fetch and re-pin."
        )
        print(msg, file=sys.stderr)
        if args.exit_loud:
            raise SystemExit(1)
        return 1

    # Also dump the actual line where the literal appears for human audit.
    for lineno, line in enumerate(blob.splitlines(), start=1):
        if defect_literal in line:
            print(f"                   defect at line : {lineno}: {line.strip()!r}")

    print("GREEN: defect literal is present at the expected count at the pinned head_sha.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

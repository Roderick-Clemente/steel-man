#!/usr/bin/env python3
"""Assert tracked docs' test-count claims against a live pytest run.

The incident this exists for: `droid-wiki/how-to-contribute/testing.md`
and `README.md` both stated "233 passed, 3 skipped" / "255 passed, 6
skipped" as present-tense facts about the suite. Both were generated-once
snapshots (the wiki page dated 2026-08-15) that nothing re-checked. By
the time it was caught, the real count was 496 passed, 6 skipped — the
wiki page alone was off by 263 tests, silently, for six weeks.

The lesson taken from that (see the PR this file shipped with): a CI
gate that blocks any edit to the doc directory would have blocked the
fix itself, since fixing the claim requires editing the file that
carries it. The actual defect wasn't "someone edited the docs" — it
was "a factual claim about live state had nothing checking it stayed
true." This script is that check: it runs the real suite and fails
loud the moment a tracked doc's claim stops matching it, regardless of
whether the doc itself was touched in the triggering change.

Usage:
    python3 tools/check_doc_test_counts.py

Exit 0: every claim matches a live run. Exit 1: at least one doesn't
(message names the file and the mismatch). Exit 2: couldn't parse a
pass count out of pytest's own output (pytest itself is broken/changed
shape — a different problem, surfaced rather than swallowed).
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Files that state the suite's CURRENT pass/skip count as a present-tense
# fact about "the suite" (as opposed to a historical record of one past
# run, e.g. an experiment writeup citing what a specific run produced —
# those are data, not a claim that needs to stay in sync, and don't
# belong in this list). Add a file here only when it makes the former
# kind of claim.
CHECKED_FILES = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "droid-wiki" / "how-to-contribute" / "testing.md",
    REPO_ROOT / "droid-wiki" / "overview" / "getting-started.md",
]

# Matches the same shape this repo already writes the claim in:
# "**496 passed, 6 skipped**". Two separate counts, not the whole
# summary line, so it doesn't care whether failures/warnings/durations
# are also mentioned nearby.
CLAIM_RE = re.compile(r"(\d+)\s+passed,\s+(\d+)\s+skipped")


def parse_pytest_summary(stdout: str) -> tuple[int, int]:
    """Extract (passed, skipped) from pytest -q's own summary line.

    Raises ValueError if a passed count can't be found — that's pytest
    itself failing to produce its normal summary shape, not a doc
    drift finding, and callers should treat it as a harder failure.
    """
    passed_match = re.search(r"(\d+) passed", stdout)
    if not passed_match:
        raise ValueError("no '<N> passed' found in pytest output")
    skipped_match = re.search(r"(\d+) skipped", stdout)
    skipped = int(skipped_match.group(1)) if skipped_match else 0
    return int(passed_match.group(1)), skipped


def find_claims(text: str) -> list[tuple[int, int]]:
    """Return every (passed, skipped) claim found in a doc's text."""
    return [(int(p), int(s)) for p, s in CLAIM_RE.findall(text)]


def run_suite() -> tuple[int, int]:
    # pytest.ini's own addopts already includes -q. Passing -q again here
    # doesn't no-op — pytest's quiet flag is cumulative, and two of them
    # push it past the level that still prints the summary line, so
    # parse_pytest_summary finds nothing and this exits 2. -o addopts=""
    # overrides the ini's addopts outright, so the only -q in effect is
    # the one below — deterministic regardless of what the ini contains
    # or changes to later.
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-o", "addopts=", "-q"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    try:
        return parse_pytest_summary(result.stdout)
    except ValueError:
        print(
            "check_doc_test_counts: could not parse a pass count from "
            "pytest's output — showing the tail for diagnosis:",
            file=sys.stderr,
        )
        print(result.stdout[-2000:], file=sys.stderr)
        sys.exit(2)


def main() -> None:
    actual_passed, actual_skipped = run_suite()
    failures: list[str] = []
    for path in CHECKED_FILES:
        if not path.exists():
            continue
        for claimed_passed, claimed_skipped in find_claims(path.read_text()):
            if (claimed_passed, claimed_skipped) != (actual_passed, actual_skipped):
                failures.append(
                    f"{path.relative_to(REPO_ROOT)}: claims "
                    f"'{claimed_passed} passed, {claimed_skipped} skipped', "
                    f"live run says "
                    f"'{actual_passed} passed, {actual_skipped} skipped'"
                )
    if failures:
        print("check_doc_test_counts: stale test-count claim(s) found:", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        print(
            "\nUpdate the doc's claim to match reality, or if a claim "
            "just moved to a new file, add that file to CHECKED_FILES "
            "in tools/check_doc_test_counts.py.",
            file=sys.stderr,
        )
        sys.exit(1)
    print(
        f"check_doc_test_counts: all claims match live run "
        f"({actual_passed} passed, {actual_skipped} skipped)"
    )


if __name__ == "__main__":
    main()

"""Tests for tools/check_doc_test_counts.py's parsing/comparison logic.

Deliberately does not shell out to run the real suite (that would make
this test ~as slow as the whole suite, and self-referential). Instead
it tests the pure functions against pytest's own stable summary-line
shape and against the real stale-claim strings this script was written
to catch, so the regression it fixes stays pinned.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import check_doc_test_counts as c  # noqa: E402


def test_parse_pytest_summary_basic():
    assert c.parse_pytest_summary("496 passed, 6 skipped in 12.34s") == (496, 6)


def test_parse_pytest_summary_with_warnings():
    assert c.parse_pytest_summary(
        "496 passed, 6 skipped, 3 warnings in 12.34s"
    ) == (496, 6)


def test_parse_pytest_summary_zero_skipped_omits_skipped_clause():
    # pytest omits the "N skipped" clause entirely when it's zero.
    assert c.parse_pytest_summary("100 passed in 1.00s") == (100, 0)


def test_parse_pytest_summary_raises_when_unparseable():
    try:
        c.parse_pytest_summary("collected 0 items / 1 error")
    except ValueError:
        return
    raise AssertionError("expected ValueError for unparseable pytest output")


def test_find_claims_matches_the_repos_own_bold_markdown_shape():
    text = "On a fresh clone the suite reports **496 passed, 6 skipped**. Done."
    assert c.find_claims(text) == [(496, 6)]


def test_find_claims_catches_the_real_stale_claims_this_script_was_built_for():
    # The two actual strings this repo shipped, pinned so a future
    # rewrite of the regex can't quietly stop catching this shape.
    assert c.find_claims("**255 passed, 6 skipped**") == [(255, 6)]
    assert c.find_claims("Expected: **233 passed, 3 skipped**.") == [(233, 3)]


def test_find_claims_returns_empty_for_a_page_with_no_claim():
    assert c.find_claims("This page has no test-count claim in it at all.") == []


def test_checked_files_list_points_at_real_files():
    for path in c.CHECKED_FILES:
        assert path.exists(), f"{path} listed in CHECKED_FILES but doesn't exist"

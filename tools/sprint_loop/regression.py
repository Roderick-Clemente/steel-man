"""Shared refusal policy for full-suite regression evidence."""

from __future__ import annotations

PYTEST_EXIT_NO_TESTS_COLLECTED = 5
PYTEST_EXIT_HARD_ERRORS = (2, 3, 4)


def regression_refusal_reason(full_suite: dict) -> str:
    """Return why a regression result is not green evidence, or ``""``.

    An absent section remains compatible with bundles produced before
    ``tests.full_suite`` existed. When the section is present, at least one
    test must pass: exit 0 with only skips proves no existing behavior.
    """
    if not full_suite:
        return ""

    exit_code = full_suite.get("suite_exit_code", 1)
    passed = full_suite.get("passed", 0)
    failed = full_suite.get("failed", 0)
    skipped = full_suite.get("skipped", 0)
    collected = passed + failed + skipped

    if failed:
        return f"{failed} failure(s) (pytest exit {exit_code})"
    if exit_code == PYTEST_EXIT_NO_TESTS_COLLECTED or collected == 0:
        return (
            f"collected no tests (pytest exit {exit_code}) — a regression run "
            f"that executed nothing is not evidence that existing behaviour "
            f"is unchanged"
        )
    if exit_code in PYTEST_EXIT_HARD_ERRORS:
        return f"pytest did not complete (pytest exit {exit_code})"
    if exit_code != 0:
        return f"pytest exit {exit_code}"
    if passed == 0:
        return (
            f"0 tests passed ({skipped} skipped, pytest exit {exit_code}) — "
            f"an all-skipped regression run is not evidence that existing "
            f"behaviour is unchanged"
        )
    return ""

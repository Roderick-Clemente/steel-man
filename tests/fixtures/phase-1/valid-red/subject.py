"""Subject under test for the valid-RED fixture — **pre-fix state**.

`running_total` carries one deliberate off-by-one bug so that
`test_valid_red.py` fails with a real behavioural `AssertionError` rather than a
syntax error, a missing import, or a tautology. That distinction is the whole
point of the fixture: `tools/phase-1-scripts/valid-red.py` must classify this
RED as VALID, and it rejects every other failure shape
(`INVALID_RED_SIGNATURES`).

The fix is exactly one line — `return totals[:-1]` becomes `return totals` —
and it lives **here**, not in the test file. That split is required, not
stylistic: `lock.py` pins the *test file's* content hash and `verify-green.py`
re-checks that hash before accepting a GREEN, so a fixture whose fix edited the
test would break its own lock and could never go green.
"""
from __future__ import annotations


def running_total(values: list[int]) -> list[int]:
    """Return the cumulative running totals of `values`.

    >>> running_total([1, 2, 3])
    [1, 3, 6]
    """
    totals: list[int] = []
    total = 0
    for value in values:
        total += value
        totals.append(total)
    # BUG (pre-fix): drops the final cumulative value. The one-line fix is to
    # return `totals`.
    return totals[:-1]

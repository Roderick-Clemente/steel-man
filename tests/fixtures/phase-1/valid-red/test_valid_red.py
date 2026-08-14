"""A **valid** RED for `tools/phase-1-scripts/valid-red.py` (spec §2.1).

The counterpart to `tests/fixtures/phase-1/invalid-red/*`: those four fixtures
each fail in a way the framework must *reject* as a RED (syntax error, missing
import, tautology, green-passing, mocked SUT). This one fails in the only way it
should *accept* — a real behavioural `AssertionError` from real code, with a
message that says what the code got wrong.

Properties the fixture has to hold, all four checked by `tools/d1-exit-check.sh`:

* **importable, no missing deps.** stdlib only, plus `subject` beside it. It
  deliberately carries no `@pytest.mark.*`: `pytest.ini` sets
  `--strict-markers`, and the `invalid-red/` fixtures next door use
  `@pytest.mark.public` and a Flask `client` fixture from the *pilot* repo, so
  they only run in that context. This one is self-contained and runs anywhere.
* **red for a real reason.** The assertion below is behavioural, so it matches
  none of `valid-red.py`'s `INVALID_RED_SIGNATURES` — not `assert 1 == 1`, not
  `assert 0 == 0`, not `MagicMock(...) is not None`, no collection error.
* **fixable.** One line in `subject.py` (`return totals[:-1]` → `return
  totals`) turns it green, which is what lets `verify-green.py` observe a real
  RED→GREEN transition rather than a file that could only ever fail.
* **lock-compatible.** The fix is in `subject.py`, never here. `lock.py` pins
  *this* file's content hash and `verify-green.py` re-checks it before accepting
  the GREEN, so a fixture that had to edit its own test to pass would break its
  own lock. See `subject.py`'s docstring.

`pytest.ini` lists `tests/fixtures` in `norecursedirs`, so this deliberately
failing test cannot redden the framework suite; it runs only when a script under
test invokes it by path.
"""
from subject import running_total


def test_running_total_includes_the_final_value():
    assert running_total([1, 2, 3]) == [1, 3, 6], (
        "running_total dropped the final cumulative value"
    )

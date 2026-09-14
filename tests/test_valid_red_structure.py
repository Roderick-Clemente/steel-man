"""Structure-first RED classification (`tools/phase-1-scripts/valid-red.py`).

These cases pin the distinction the classifier previously could not make:
a test file that *never ran* because it could not be imported, versus a test
that ran, reached a real assertion, and quoted an import error in its failure
message. Only the first is an invalid RED. The second is the ordinary shape of
a good RED for a not-yet-existing module, and rejecting it blocked every chunk
that introduces one — while rewarding tests that say nothing about why they are
red.

The classifier is exercised through `classify()` on captured pytest output
rather than by shelling out, so each structural shape (collection ERROR, zero
collected, executed FAILURES) can be stated exactly.
"""

from __future__ import annotations

import importlib.util
import os

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT_PATH = os.path.join(REPO_ROOT, "tools", "phase-1-scripts", "valid-red.py")


def _load_classifier():
    """Load valid-red.py as a module without running main()."""
    spec = importlib.util.spec_from_file_location("valid_red_structure", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def vr():
    return _load_classifier()


# --- captured output fixtures ------------------------------------------------

# Real-world shape, captured from a pilot run: a seven-test locked file for a
# module that does not exist yet. The file imports the subject inside a guard
# and carries the captured cause in its assertion message, so
# `ModuleNotFoundError:` appears *inside* an `E   AssertionError:` line while
# the run collected and executed all seven tests. This is a VALID RED.
EXECUTED_FAILURE_QUOTING_IMPORT_ERROR = """\
============================= test session starts ==============================
platform darwin -- Python 3.12.12, pytest-9.1.1, pluggy-1.6.0
rootdir: /pilot
collected 7 items

tests/test_homes_store.py::test_empty_or_absent_store FAILED             [ 14%]
tests/test_homes_store.py::test_homes_can_be_created FAILED              [ 28%]
tests/test_homes_store.py::test_devices_are_scoped_to_home FAILED        [ 42%]
tests/test_homes_store.py::test_legacy_store_upgrades_once FAILED        [ 57%]
tests/test_homes_store.py::test_cache_and_layout_unchanged FAILED        [ 71%]
tests/test_homes_store.py::test_room_membership_is_scoped FAILED         [ 85%]
tests/test_homes_store.py::test_deleted_home_is_reported_missing FAILED  [100%]

=================================== FAILURES ===================================
_________________________ test_empty_or_absent_store __________________________

bundle = ServiceBundle(hs=None, hs_error="homes_store: ...")

    def _require_home_service(bundle: ServiceBundle) -> Any:
>       assert bundle.hs is not None, bundle.hs_error
E       AssertionError: homes_store: app.services.home_service must exist \
(import failed: ModuleNotFoundError: No module named 'app.services.home_service')
E       assert None is not None

tests/test_homes_store.py:159: AssertionError
=========================== short test summary info ============================
FAILED tests/test_homes_store.py::test_empty_or_absent_store - AssertionError: \
homes_store: app.services.home_service must exist (import failed: \
ModuleNotFoundError: No module named 'app.services.home_service')
============================== 7 failed in 0.42s ===============================
"""

# The genuine article: the file itself cannot be imported, so pytest reports a
# collection ERROR and runs zero tests.
COLLECTION_ERROR_MISSING_MODULE = """\
============================= test session starts ==============================
collected 0 items / 1 error

==================================== ERRORS ====================================
_________________ ERROR collecting tests/test_homes_store.py __________________
ImportError while importing test module '/pilot/tests/test_homes_store.py'.
Traceback:
tests/test_homes_store.py:4: in <module>
    from app.services.home_service import HomeService
E   ModuleNotFoundError: No module named 'app.services.home_service'
=========================== short test summary info ============================
ERROR tests/test_homes_store.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
=============================== 1 error in 0.11s ===============================
"""

SYNTAX_ERROR_COLLECTION = """\
============================= test session starts ==============================
collected 0 items / 1 error

==================================== ERRORS ====================================
_________________ ERROR collecting tests/test_homes_store.py __________________
tests/test_homes_store.py:12: in <module>
E     File "/pilot/tests/test_homes_store.py", line 12
E       assert result == {"homes_store": 1
E                        ^
E   SyntaxError: '{' was never closed
=========================== short test summary info ============================
ERROR tests/test_homes_store.py
=============================== 1 error in 0.09s ===============================
"""

EMPTY_SELECTION = """\
============================= test session starts ==============================
collected 0 items

============================ no tests ran in 0.01s =============================
"""

PASSING_RUN = """\
============================= test session starts ==============================
collected 2 items

tests/test_homes_store.py::test_homes_store_exists PASSED                [ 50%]
tests/test_homes_store.py::test_homes_store_scopes PASSED                [100%]

=============================== 2 passed in 0.05s ==============================
"""

TAUTOLOGICAL_EXECUTED_FAILURE = """\
============================= test session starts ==============================
collected 2 items

tests/test_homes_store.py::test_homes_store_placeholder FAILED           [ 50%]
tests/test_homes_store.py::test_homes_store_other FAILED                 [100%]

=================================== FAILURES ===================================
_________________________ test_homes_store_placeholder ________________________

    def test_homes_store_placeholder():
>       assert True
E       assert True

tests/test_homes_store.py:9: AssertionError
=========================== short test summary info ============================
FAILED tests/test_homes_store.py::test_homes_store_placeholder
============================== 2 failed in 0.03s ===============================
"""

MOCKED_SUBJECT_EXECUTED_FAILURE = """\
============================= test session starts ==============================
collected 1 item

tests/test_homes_store.py::test_homes_store_reads FAILED                 [100%]

=================================== FAILURES ===================================
____________________________ test_homes_store_reads ___________________________

    def test_homes_store_reads():
        mock = MagicMock()
>       assert mock.list_homes() == ["homes_store"]
E       AssertionError

tests/test_homes_store.py:14: AssertionError
=========================== short test summary info ============================
FAILED tests/test_homes_store.py::test_homes_store_reads
============================== 1 failed in 0.03s ===============================
"""

# Same structural shape as the valid case, but the accepted-assertion phrase is
# nowhere in the output.
EXECUTED_FAILURE_WITHOUT_ACCEPTED_ASSERTION = """\
============================= test session starts ==============================
collected 1 item

tests/test_widgets.py::test_widget_totals FAILED                         [100%]

=================================== FAILURES ===================================
_____________________________ test_widget_totals ______________________________

    def test_widget_totals():
>       assert widget_totals([1, 2]) == [1, 3]
E       AssertionError: widget_totals dropped the final value

tests/test_widgets.py:7: AssertionError
=========================== short test summary info ============================
FAILED tests/test_widgets.py::test_widget_totals
============================== 1 failed in 0.03s ===============================
"""

EXECUTED_FAILURE_WITH_CONFTST_WARNING = """\
============================= test session starts ==============================
collected 1 item

tests/test_widgets.py::test_widget_totals FAILED                         [100%]

=================================== FAILURES ===================================
_____________________________ test_widget_totals ______________________________

    def test_widget_totals():
>       assert widget_totals([1, 2]) == [1, 3]
E       AssertionError: widget totals preserve the final value

tests/test_widgets.py:7: AssertionError
=============================== warnings summary ===============================
tests/conftest.py:5
  /pilot/tests/conftest.py:5: PytestDeprecationWarning: legacy fixture scope
    @pytest.fixture

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED tests/test_widgets.py::test_widget_totals - AssertionError: widget totals preserve the final value
========================= 1 failed, 1 warning in 0.03s =========================
"""


# --- the regression that motivated the fix -----------------------------------


def test_executed_failure_may_quote_an_import_error_in_its_message(vr):
    result = vr.classify(1, EXECUTED_FAILURE_QUOTING_IMPORT_ERROR, "", "homes_store")
    assert result["valid"] is True, result["reason"]


def test_structure_shows_seven_tests_executed(vr):
    """The evidence the text match ignored: a FAILURES section and FAILED lines."""
    assert "collected 7 items" in EXECUTED_FAILURE_QUOTING_IMPORT_ERROR
    assert vr.failures_region(EXECUTED_FAILURE_QUOTING_IMPORT_ERROR).strip()
    assert vr.collection_error_region(EXECUTED_FAILURE_QUOTING_IMPORT_ERROR).strip() == ""
    assert "ModuleNotFoundError" not in vr.outside_failures_region(
        EXECUTED_FAILURE_QUOTING_IMPORT_ERROR
    )


# --- the guard still guards --------------------------------------------------


def test_real_collection_failure_is_invalid(vr):
    result = vr.classify(2, COLLECTION_ERROR_MISSING_MODULE, "", "homes_store")
    assert result["valid"] is False
    assert result["reason"] == "Invalid RED: missing module import"
    assert vr.collection_error_region(COLLECTION_ERROR_MISSING_MODULE).strip()
    assert vr.failures_region(COLLECTION_ERROR_MISSING_MODULE).strip() == ""


def test_syntax_error_preventing_collection_is_invalid(vr):
    result = vr.classify(2, SYNTAX_ERROR_COLLECTION, "", "homes_store")
    assert result["valid"] is False
    assert result["reason"] == "Invalid RED: syntax error"


def test_empty_selection_is_invalid(vr):
    result = vr.classify(5, EMPTY_SELECTION, "", "homes_store")
    assert result["valid"] is False
    assert result["reason"] == "Invalid RED: empty test selection"


def test_passing_run_is_invalid(vr):
    result = vr.classify(0, PASSING_RUN, "", "homes_store")
    assert result["valid"] is False
    assert result["reason"] == "Invalid RED: test passed (no failure to fix)"


def test_tautological_assertion_in_executed_failure_is_invalid(vr):
    result = vr.classify(1, TAUTOLOGICAL_EXECUTED_FAILURE, "", "homes_store")
    assert result["valid"] is False
    assert result["reason"] == "Invalid RED: tautological assertion"


def test_mocked_subject_in_executed_failure_is_invalid(vr):
    result = vr.classify(1, MOCKED_SUBJECT_EXECUTED_FAILURE, "", "homes_store")
    assert result["valid"] is False
    assert result["reason"] == "Invalid RED: subject under test mocked"


def test_missing_accepted_assertion_is_invalid(vr):
    result = vr.classify(1, EXECUTED_FAILURE_WITHOUT_ACCEPTED_ASSERTION, "", "homes_store")
    assert result["valid"] is False
    assert result["reason"] == "Invalid RED: failure does not match accepted assertion"


def test_warnings_summary_does_not_make_an_executed_failure_a_conftest_error(vr):
    result = vr.classify(
        1, EXECUTED_FAILURE_WITH_CONFTST_WARNING, "", "widget totals preserve the final value"
    )
    assert result["valid"] is True, result["reason"]
    assert "conftest.py" not in vr.outside_failures_region(EXECUTED_FAILURE_WITH_CONFTST_WARNING)


# --- signature list shape ----------------------------------------------------


def test_signature_groups_are_disjoint(vr):
    groups = (
        vr.COLLECTION_PHASE_SIGNATURES,
        vr.TEST_QUALITY_SIGNATURES,
        vr.ENVIRONMENT_SIGNATURES,
    )
    signatures = [signature for group in groups for signature in group]
    assert len(signatures) == len(set(signatures))

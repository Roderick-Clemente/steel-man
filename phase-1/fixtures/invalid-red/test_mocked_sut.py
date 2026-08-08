"""Invalid-RED fixture: subject under test mocked.

This test file replaces the SUT (the /llms.txt response) with a MagicMock,
then asserts on the mock. The real handler is never called. The mock is
configured with a doubled charset so the assertion fails, causing pytest to
show the test source (including `mock = MagicMock()`) in the traceback.
The classifier detects the mock pattern and rejects the RED.

Expected classifier output:
  valid: false
  reason: "Invalid RED: subject under test mocked"
"""

from unittest.mock import MagicMock

import pytest


@pytest.mark.public
def test_llms_txt_mocked_sut():
    # Subject under test is mocked — the real handler is never called
    mock = MagicMock()
    mock.headers = {"Content-Type": "text/plain; charset=utf-8; charset=utf-8"}
    mock.status_code = 200
    mock.get_data.return_value = "Quantum Bank"

    response = mock
    assert response.status_code == 200
    assert "Quantum Bank" in response.get_data(as_text=True)

    content_type = response.headers.get("Content-Type", "")
    charset_count = content_type.lower().count("charset=")
    assert charset_count == 1, (
        "Content-Type contains exactly one charset= token "
        f"(found {charset_count} in {content_type!r})"
    )

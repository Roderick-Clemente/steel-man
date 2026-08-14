"""Invalid-RED fixture: tautological assertion.

This test file contains `assert True` and `assert 1 == 1` — tautologies that
always pass regardless of the system under test. When run at the pre-fix
commit, the later charset assertion also fails, so the test exits non-zero
and pytest shows the full test source (including the tautological lines) in
the failure traceback. The classifier detects the tautological pattern and
rejects the RED.

Must be run at the pre-fix commit (api/llms_txt.py with
mimetype="text/plain; charset=utf-8") so the charset assertion fails and
the test source appears in the traceback.

Expected classifier output:
  valid: false
  reason: "Invalid RED: tautological assertion"
"""

import pytest


@pytest.mark.public
def test_llms_txt_tautological(client):
    response = client.get("/llms.txt")

    assert response.status_code == 200

    # Tautological assertions — always true, exercise nothing
    assert True
    assert 1 == 1

    body = response.get_data(as_text=True)
    assert "Quantum Bank" in body

    # This assertion fails at the pre-fix commit (doubled charset),
    # causing pytest to show the test source including the tautologies above
    content_type = response.headers.get("Content-Type", "")
    charset_count = content_type.lower().count("charset=")
    assert charset_count == 1, (
        "Content-Type contains exactly one charset= token "
        f"(found {charset_count} in {content_type!r})"
    )

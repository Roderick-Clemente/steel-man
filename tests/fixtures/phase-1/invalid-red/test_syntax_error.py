"""Invalid-RED fixture: SyntaxError.

This test file has an intentional syntax error (missing closing parenthesis).
The classifier should reject this as 'syntax error' because the test never
collected or executed — it failed at parse time.

Expected classifier output:
  valid: false
  reason: "Invalid RED: syntax error"
  exit_code: 2 (pytest collection error)
"""

import pytest


@pytest.mark.public
def test_llms_txt_syntax_error(client):
    response = client.get("/llms.txt")

    assert response.status_code == 200
    # Intentional syntax error: missing closing parenthesis
    assert "Quantum Bank" in response.get_data(as_text=True

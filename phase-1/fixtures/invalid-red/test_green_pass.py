"""Invalid-RED fixture: no failure (green).

This test file comments out the assertion that would fail (the charset count
check). All prior assertions pass, so the test exits 0. The classifier should
reject this as 'test passed (no failure to fix)' because there is no RED.

Expected classifier output:
  valid: false
  reason: "Invalid RED: test passed (no failure to fix)"
  exit_code: 0
"""

import pytest


@pytest.mark.public
def test_llms_txt_green(client):
    response = client.get("/llms.txt")

    assert response.status_code == 200

    body = response.get_data(as_text=True)
    assert "Quantum Bank" in body
    assert "Split.io" in body

    content_type = response.headers.get("Content-Type", "")
    media_type = content_type.split(";")[0].strip().lower()
    assert media_type == "text/plain", (
        f"Content-Type media type is {media_type!r}, expected 'text/plain' "
        f"(full header: {content_type!r})"
    )

    # The assertion that would fail is commented out — test passes (GREEN)
    # charset_count = content_type.lower().count("charset=")
    # assert charset_count == 1, (
    #     "Content-Type contains exactly one charset= token "
    #     f"(found {charset_count} in {content_type!r})"
    # )

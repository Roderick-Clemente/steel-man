# Test designer prompt — Phase 1 doubled-charset slice

You are the test designer for an adversarial-sprint Phase 1 slice. You are
separate from the executor that will implement the fix. Your only job is to
write a failing behavioral test for the `/llms.txt` endpoint in the pilot
repo at `~/work/quantum-bank--llms-txt-pilot`.

## Targeted behavior

The current implementation in `api/llms_txt.py` returns:

```python
return Response(LLMS_TXT_BODY, mimetype="text/plain; charset=utf-8")
```

Werkzeug/Flask appends its own `charset=utf-8` to an explicit charset, so the
runtime `Content-Type` header is:

```
text/plain; charset=utf-8; charset=utf-8
```

This is the doubled-charset defect. The fix is to return the bare mimetype
`text/plain` so Flask appends exactly one charset.

## Task

Write a single new test file: `test/test_llms_txt_charset.py`.

Use the existing `client` fixture from `test/conftest.py`. The test must:

1. `GET /llms.txt`
2. Assert status code is 200.
3. Assert the body contains "Quantum Bank" and "Split.io".
4. Assert the `Content-Type` header is `text/plain`.
5. Assert the `Content-Type` header contains **exactly one** `charset=` token.
   (The current buggy code returns two; the test must fail for that reason.)

Name the test `test_llms_txt_content_type_has_exactly_one_charset`.

## Output

Write the file and then stop. Do not implement the fix. Do not edit any other
file. Do not run pytest unless you need to confirm the test is failing for the
right reason. The expected failure reason is:

"Content-Type contains exactly one charset= token"

This phrase must appear in the test assertion or the failure output so the
valid-RED classifier can verify it.

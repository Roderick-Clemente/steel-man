# Executor prompt — Phase 1 doubled-charset slice

You are the executor for an adversarial-sprint Phase 1 slice. You are separate
from the test designer. Your job is to fix the implementation so the locked
test passes, without touching any test file.

## Locked test

The test file `test/test_llms_txt_charset.py` is locked and must not be
modified. It asserts that `GET /llms.txt` returns a `Content-Type` header
containing exactly one `charset=` token.

## Current bug

`api/llms_txt.py` currently returns:

```python
return Response(LLMS_TXT_BODY, mimetype="text/plain; charset=utf-8")
```

This causes Werkzeug to double-append `charset=utf-8`, producing:

```
text/plain; charset=utf-8; charset=utf-8
```

## Fix

Change `api/llms_txt.py` to return the bare mimetype so Flask/Werkzeug appends
exactly one charset:

```python
return Response(LLMS_TXT_BODY, mimetype="text/plain")
```

## Constraints

- You may only edit `api/llms_txt.py`.
- You may NOT edit `test/test_llms_txt_charset.py` or any other file under
  `test/`.
- Do not run the test suite yourself; the green verifier will run it after you
  finish.
- If you are blocked, report the blocker and stop.

## Output

Apply the one-line change to `api/llms_txt.py` and stop.

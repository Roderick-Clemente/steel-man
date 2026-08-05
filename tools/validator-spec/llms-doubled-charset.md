# Validator spec — /llms.txt doubled-charset defect

## What is under review
A `git diff` against `api/llms_txt.py` and related wiring. The diff shows the
TEXTBOOK shape of a "Write `mimetype='text/plain; charset=utf-8'`" in a Flask
Response constructor. Werkzeug 3.x emits the response Content-Type as
`text/plain; charset=utf-8; charset=utf-8` for that exact input. That is
doubled-charset; RFC 9110 §8.3 says a Content-Type header SHOULD NOT
contain duplicate parameters.

## Acceptance gate
You MUST surface the doubled-charset defect in your verdict. Verdict MUST
NOT be `ACCEPT` if the diff introduces `mimetype="text/plain; charset=utf-8"`
without a corrigendum (a bare `text/plain` is fine; the doubled-charset
comes from including an explicit `charset=` token when Werkzeug appends one
itself).

## Decision rubric
ACCEPT
  no defect introduced; findings are minor or stylistic (off-spec but
  benign).

ACCEPT-WITH-NITS
  a defect is acknowledged as a minor finding, the relevant section is
  named, and the correction is named (bare `text/plain`).

REJECT
  the doubled-charset is treated as a major defect, the human must fix
  it before production.

## Failure evidence required in the verdict
- The line in the diff where `mimetype="text/plain; charset=utf-8"` appears.
- The expected Content-Type result `text/plain; charset=utf-8; charset=utf-8`
  with `charset=` tokens counted.

## What you do NOT get
You do not get the executor's BUILD-LOG, transcripts, prior conversation,
hook attempts, or model-availability records. The diff is the universe.

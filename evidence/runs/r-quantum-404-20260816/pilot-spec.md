# Pilot spec — content-negotiated 404s for QuantumBank

## Context
QuantumBank is a small Flask app. It registers a single Flask 404 error
handler (`app.py` -> `@app.errorhandler(404)` -> `api/four_o_four.py:handle_404`).
`handle_404` currently returns a bare string, so Flask serves every 404 as
`Content-Type: text/html`. The app also exposes a JSON API under `/api/*`
(see `api/api_endpoints.py`, which returns `jsonify({"error": ...}), <code>`
for its own error cases).

## Problem
A client calling a nonexistent `/api/*` path receives an HTML-ish 404 body it
cannot parse as JSON. The 404 handler does not distinguish API requests from
browser requests.

## Goal (single slice)
Make 404 responses content-negotiated:
- Requests under `/api/*` receive a parseable JSON error body with
  `Content-Type: application/json`.
- All other (non-API) paths keep the existing HTML 404 behavior.

## Acceptance criteria (observable)
1. `GET` a nonexistent `/api/*` path returns HTTP 404.
2. That response `Content-Type` starts with `application/json`.
3. That response body parses as JSON and contains an `error` key.
4. `GET` a nonexistent non-API path returns HTTP 404 with `Content-Type`
   starting with `text/html`.
5. The existing test suite continues to pass.

## Scope
- In scope: 404 handling only.
- Out of scope: any other route, any other status code, response schema
  changes to existing endpoints, logging, auth.

## Test surface
- Locked test file: `test/test_api_routes.py` (already contains the RED
  tests for criteria 1-4).
- Allowed implementation files: `api/four_o_four.py`, `app.py`.

## Notes
This spec states the problem and the acceptance criteria only. It does not
prescribe an implementation; the executor decides how to satisfy the tests.

# Valid-RED classifier

PRD §5.4 says a valid RED means the test collected, executed the intended
path, reached its assertion, and failed because the required behavior is
absent or wrong. Syntax errors, import errors, missing fixtures, unavailable
services, empty test selection, timeouts, and unrelated assertion failures are
invalid RED.

This Phase 1 classifier implements that definition for the doubled-charset
slice on `~/work/quantum-bank--llms-txt-pilot`.

## Rejection criteria (invalid RED)

The classifier rejects the RED run when any of these are observed in the
pytest output:

1. **Syntax or import failures**
   - `SyntaxError`
   - `IndentationError`
   - `ModuleNotFoundError`
   - `ImportError`
   - `FixtureLookupError`
   - `conftest.py` error
   - `collection error`

2. **Tautological or vacuous tests**
   - `assert True`
   - `assert 1 == 1`
   - `assert 0 == 0`

3. **Subject under test mocked**
   - `mock = MagicMock(...)`
   - `MagicMock(...) is not None`

4. **No failure occurred**
   - pytest exit code 0 with a passing result
   - pytest exited non-zero but no `FAILED` or `failures` marker is present
   - pytest collected 0 items / "no tests ran" / "test selection empty"

5. **Service unavailable**
   - The run emitted `unavailable`, `service ... unavailable`,
     `connection refused`, or `could not connect to` markers. The
     assertion is allowed to fail in this case (no scope to fix), so
     treat the RED as invalid until the service is reachable.

6. **Failure is unrelated to the accepted assertion**
   - The accepted assertion phrase (e.g., "Content-Type contains exactly one
     charset= token") does not appear in the combined stdout/stderr.

## Acceptance criteria (valid RED)

A RED is accepted only when:

1. pytest reports a non-zero exit code,
2. pytest reports at least one `FAILED` test,
3. none of the invalid-RED signatures are present, and
4. the accepted assertion phrase appears in the output (the intended
   assertion ran and failed).

## Why this is intentionally not a full parser

The classifier reads the pytest output rather than the test source because the
run is the evidence. A test file can look correct and still fail for the wrong
reason (e.g., a fixture mismatch or an environment issue). The gate must decide
whether the *run* proves the intended behavior is missing, not whether the
*source* looks plausible.

## Limitations for this slice

- The assertion-phrase match is a substring check. For this slice the phrase is
  written by the test designer and recorded in the lock manifest, so it is a
  stable contract.
- The classifier does not inspect hidden test files. It only looks at the
  locked test file passed on the command line.
- Timeouts are treated as invalid RED.

See `phase-1/scripts/valid-red.py` for the implementation.

# Phase 3.2 — Assumptions & gaps log

First-class deliverable per RUN-PROMPT.md. Every point where the spec did not
fully determine what to build: (a) the decision, (b) why, (c) what was missing
or ambiguous.

---

## 1. Bundle signature scheme

- **Decision:** HMAC-SHA256 with a key from an env var (`EVIDENCE_SIGNING_KEY`,
  default `"local-default-key"`), key_id recorded in the signature.
- **Why:** The SPIKE (§8) explicitly defers the signature scheme as "an
  implementation detail of 'producer is not spoofable in-context'." HMAC-SHA256
  is the simplest scheme that satisfies "not spoofable inside an agent's
  context" — an agent that fabricates a bundle cannot sign it without the key.
  Ed25519 would be stronger but adds a key-management dependency for no
  marginal benefit in the local-backend-only scope of this run.
- **Missing in spec:** §8 names it as deferred. The key distribution model
  (how the consumer gets the key to verify) is also unspecified. For local mode
  the default key is known; for Harness mode this would need a real key
  distribution path.

## 2. Token estimation method

- **Decision:** `chars // 4` as the token proxy for both raw output and bundle.
- **Why:** The SPIKE §3.2 says to "count the MCP call + returned payload tokens"
  but does not specify the estimation method. chars/4 is the standard proxy for
  English/JSON text and is sufficient for directional comparison. The real H-CI
  experiment would use each provider's tokenizer for exact numbers.
- **Missing in spec:** No tokenizer or estimation method specified. The fairness
  rule is stated as a comparison (`bundle < raw output`), not an absolute
  measurement, so the proxy is adequate for the directional result.

## 3. Bandit as the local scanner (not Semgrep)

- **Decision:** Bandit only (not both Semgrep and Bandit).
- **Why:** RECOMMENDATION.md says "Semgrep and Bandit (both)" but Semgrep was
  not installed and Bandit was already available via pip. The SPIKE §8 says
  "pick at prototype time; the interface does not care." Bandit covers Python
  security linting which is sufficient for the pilot (a Flask/Python app). Adding
  Semgrep is a small extension behind the same interface.
- **Missing in spec:** §8 explicitly leaves this open. RECOMMENDATION.md
  recommended both, but the interface is scanner-agnostic.

## 4. Bandit `.venv` exclusion path format

- **Decision:** Exclude paths must use `./` prefix (`./.venv,./.git`), not bare
  names (`.venv,.git`).
- **Why:** Bandit's `-x` flag uses `pathlib.Path.match()` which requires the
  `./` prefix to match paths as reported in results. Without it, the exclusion
  silently fails and 2024 findings from installed packages drown the signal.
- **Missing in spec:** Not a spec gap — a tool-specific implementation detail.
  Recorded because it is the kind of thing that costs time and should not cost
  it again.

## 5. Security findings: only NEW in the bundle

- **Decision:** Only findings where `is_new=true` enter the bundle's
  `security.findings[]`. Baseline debt is excluded entirely.
- **Why:** The SPIKE §2.1 says "compact by construction" and §4.4 says "gate on
  new-vs-baseline." Including 294 baseline findings would make the bundle
  hundreds of KB — defeating the compactness requirement. The bundle is for
  THIS change's evidence; baseline debt is a standing report, not a per-change
  artifact.
- **Missing in spec:** §2.1 shows `security.findings[]` without saying whether
  it carries all findings or only new ones. §4.4 says the gate keys on new
  only, which implies the bundle should surface new. The decision follows that
  implication but the spec does not state it explicitly.

## 6. Full-suite vs locked-test-only in the `tests` section

- **Decision:** Added `--full-suite` flag; when set, the `tests` section carries
  the full regression suite results (103 tests), not just the locked test (3).
  The `locked_test_sha_observed` always comes from verify-green.py on the locked
  test regardless.
- **Why:** Phase 3 validators ran both `pytest test/test_profile_model.py -v`
  and `pytest -q` (full regression). The bundle replaces BOTH outputs. Without
  the full suite, the token comparison would be misleading — the bundle would
  look larger than the locked-test output alone, but smaller than the combined
  output the validator actually consumed.
- **Missing in spec:** §2.1 shows `tests: passed/failed/skipped` without
  specifying whether this is the locked test or the full suite. The
  `locked_test_sha_observed` is clearly the locked test, but the test counts
  are ambiguous. The `--full-suite` flag makes this configurable; the demo
  uses it.

## 7. Coverage lens not functional

- **Decision:** Coverage is a best-effort optional; in the demo it returned
  `None` (pytest-cov not configured for the target file). The bundle omits the
  `coverage` section when unavailable.
- **Why:** The pilot's pytest-cov is configured for the whole suite, not
  individual test files. The coverage parsing is implemented but did not
  produce results for this run. This is a tooling gap, not a design gap.
- **Missing in spec:** §2.1 marks coverage as optional. Not a spec gap.

## 8. SCHEMA bump on a feature branch

- **Decision:** The SCHEMA.md bump (v1→v2, test-designer role, MCP token fields)
  is on the `factory/phase-3.2-evidence` feature branch.
- **Why:** AGENTS.md says "keep convention/spec changes off feature branches so
  they don't ride along with unreviewed work." However, RUN-PROMPT.md step 2
  explicitly says "Do the SCHEMA bump before writing bundle-emitting code."
  The tension is resolved by: the bump is small, additive (all new fields are
  optional), and explicitly mandated by the human-approved spec. It lands on
  `main` only after cross-family review, same as everything else.
- **Missing in spec:** Not a spec gap — a process tension between two
  instructions. Flagged for the reviewer.

## 9. `change_ref.locked_test_sha` as input vs observed

- **Decision:** The local backend computes `locked_test_sha_observed` by running
  verify-green.py (which recomputes the sha and compares to the manifest). The
  `change_ref.locked_test_sha` input from SPIKE §2.1 is not passed as a separate
  argument — the lock file IS the manifest, and verify-green.py does the
  comparison. The observed sha is what verify-green.py actually hashed.
- **Why:** The SPIKE shows `locked_test_sha` as a REQUIRED input to the
  provider, but verify-green.py already reads the lock manifest and computes the
  sha. Passing the expected sha separately would duplicate what verify-green.py
  already does. The provider passes the lock file; verify-green.py does the
  rest.
- **Missing in spec:** §2.1 shows `locked_test_sha` as an input to
  `get_evidence(change_ref)`, but the local backend has access to the lock
  manifest directly. The interface could take the sha or the manifest path;
  this implementation takes the manifest path.

## 10. Consumer does not re-run pytest or read the diff

- **Decision:** `ValidatorConsumer` reaches an evidence-only verdict (ACCEPT if
  tests pass + signature valid, REJECT otherwise). It does not read the diff or
  spec. The full validator verdict (including cross-family diff review) is
  out of scope for this consumer and remains the panel's job (SPIKE §4.3).
- **Why:** §4.3 is explicit: "CI augments, does not replace, the panel." The
  consumer handles only the deterministic-evidence portion.
- **Missing in spec:** Not a gap — the spec is clear. Recorded to prevent the
  misreading that this consumer is a full validator replacement.

## 11. No MCP wiring (local mode only)

- **Decision:** No MCP server or tools are wired. The local backend produces the
  bundle in-process; the consumer reads it from disk. There is no inbound MCP
  edge.
- **Why:** SPIKE §6 says "In the local mode there is no inbound edge at all;
  the local backend produces the bundle in-process." This run is explicitly
  local-only (RUN-PROMPT scope: "no CI and no Harness").
- **Missing in spec:** Not a gap. The Harness MCP inbound edge is explicitly
  out of scope for this run.

## 12. Token accounting uses combined raw output

- **Decision:** The fairness comparison uses the combined raw output of the
  locked test (`-v`) plus the full regression suite (`-q`), since Phase 3
  validators consumed both. A separate comparison with only the locked test
  output is also captured.
- **Why:** The validator prompt (Phase 3) instructs running both `pytest
  test/test_profile_model.py -v` and `pytest -q`. The bundle replaces both.
  Comparing against only one would misrepresent the control arm.
- **Missing in spec:** §3.2 says "tokens(in-session raw test output it
  replaces)" without specifying whether "raw test output" is the locked test,
  the full suite, or both. The Phase 3 validator prompts show both were run.

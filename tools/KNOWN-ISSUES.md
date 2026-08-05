# tools/ — KNOWN ISSUES

Tracked defects the validation pipeline has exposed but which the
brief's HARD STOP has placed OUT OF SCOPE for rung 7 closure.

## Issue: False-REJECT via source-read (isolation leak)

- **Status:** confirmed hole; rung-8+ / OUT OF SCOPE.
- **Surface:** rung 7, gate axes rung-3 / rung-5 / rung-6.
- **Filed:** 2026-08-04.

### Symptom

When the validator is pointed at an empty diff with the default
tool set (`Read,Execute,Glob,Grep,LS`), the validator reads
`api/llms_txt.py` from the source clone, fabricates a REJECT
verdict with a substantive doubled-charset finding, and passes
all three gates. Pipeline fails to fail loud — the validator over-
claims based on source inspection rather than the diff under review.

### Repro (commit `2098859`)

- **Config A — empty diff; default tools.**
  ```
  --model gpt-5.4-mini
  --enabled-tools Read,Execute,Glob,Grep,LS
  --cwd /tmp/rung7-fresh-clone-1785874884   (HEAD = 2b70eae1)
  ```
  Verifier verdict (verbatim):
  ```
  # REJECT
  ## Finding: doubled `charset` on `/llms.txt`
  `api/llms_txt.py` returns `Response(..., mimetype='text/plain;
  charset=utf-8')`, which makes Werkzeug append its own charset
  and yields a doubled `Content-Type`.
  ```
  num_turns=3, is_error=false. Validator ran 3 Read tool calls and
  acquired the answer from source. rung-3 GREEN, rung-5 GREEN.

- **Config B — empty diff + blocked-Read tools.**
  ```
  --model gpt-5.4-mini
  --enabled-tools Execute,Glob         # Read + Grep stripped
  --cwd /tmp/rung7-configB-1785875095
  ```
  Verifier verdict:
  ```
  # ACCEPT
  DIFF IS EMPTY and the available tools cannot verify any
  doubled-charset defect.
  ```
  num_turns=1, is_error=false, 0 tool_use events. rung-3 RED,
  rung-5 RED, rung-6 RED.

### Root cause

The validator operates against a fresh clone of the source repo on
tool `Read`. Its tool allowlist covers the whole clone, so its
review is functionally "inspect repo state" — not "inspect the
diff under review". The diff under review is `BASE → HEAD`, but
the absolute file paths it sees are bound to a working tree that
includes pre-existing source it must ignore. There is no
isolation layer that scopes tool access to just the diff hunks.

This is an isolation leak: a defensive validator that knows it
should "grade the diff" but whose tool surface lets it read the
underlying repo will, under default config, collapse to "grade the
repo". The gate contract cannot distinguish false-claim from
genuine-claim when both present as a properly-formed REJECT with
a doubled-charset phrasing.

### Candidate fixes (ranked)

1. **Harness-level no-op detection.** When the diff under review
   is empty, force-enable `--enabled-tools ""` (or the per-platform
   equivalent) so the validator cannot exercise any inspection tool.
   If the verifier still emits a substantive verdict against tool
   silence, that fact is automatically a rung-3 / rung-5 gate miss
   (zero tool calls + non-empty verdict). This is the cheapest
   rung-8 fix; it changes the gate, not the validator.

2. **Scope tool access to the diff hunks.** Build a sandbox where
   the validator's `Read` tool is filtered by the `diff_paths`
   list (in our fixture: `api/llms_txt.py`, `app.py`,
   `test/test_public_routes.py`). Out-of-scope files become
   unreadable. The validator's defensible review surface becomes
   limited to the diff subject. This is more invasive — it
   requires a tool adapter layer that the droid CLI does not
   directly expose today.

Either fix moves rung-7 Config A from "passes the gates falsely" to
"fails the gates loudly", satisfying the brief's "fail-loud"
intent. Both belong in rung-8+; neither is being implemented in this
rung-7 cleanup pass.

### Why this is OUT OF SCOPE now

- Brief's HARD STOP after rung 7: no rung 8, no new gates, no new
  routes. Implementing either fix above would change either the
  validator invocation contract (candidate 1) or the tool surface
  (candidate 2), and would require either a re-run or a tool-
  adapter scaffold.

- It is logged here so that when rung-8 work is approved, this hole
  is the first item. The reproducer is in
  `tools/fixtures/rung7-reflection.md` and the
  `rung7-config{B,A}-digest.json` fit the rung-8 verification gate.

### Related issues to be filed (and not fixed now)

- **Stale "/tmp/rungn-fresh-clone-…" path references in the
  digests.** These point at ephemeral Linux dirs and session
  machinery that does not survive a reboot. They are captured as
  evidence of the run, not as durable handling. A future rung-9
  pass should either strip these or alias them via a
  reproducible machine name.

- **Validator's severity rubric runs hotter than the four-family
  rubric.** Documented in `tools/fixtures/rung7-reconciliation.md`
  (corrected analysis). The validator (gpt-5.4-mini) over-claims
  severity for defects the four hand-relayed model families
  (Grok/Kimi/Codex/Opus) let pass as nits. (See "Severity rubric
  divergence on identical input.")

- **rung-4 "family" key uses provider, not model lineage.**
  When the MiniMax and Kimi models both run on Fireworks,
  rung-4 would falsely classify them as the same family; the
  brief's intent is "model lineage", not "serving provider".
  Config-contract TODO. Documented in `tools/README.md`.

## Issue: Fake-pass via unmatched tool_use (is_error=None)

- **Status:** CONFIRMED; closeable in unit C of the same ladder.
- **Surface:** rung 3 / rung 5 / rung 6 — all three simultaneously.
- **Filed:** 2026-08-05 (rung 5.5 unit A).

### Mechanism — three holes align

1. **`tools/adapters/factory.py`** (line ~210):
   `_extract_tool_calls_from_session_jsonl` returns one dict per
   matched-OR-unmatched `tool_use` event. When a `tool_use` has
   no matching `tool_result` in the same inner-session jsonl, the
   dict reports `is_error=None` (default for missing dict key on
   `tool_results_by_id.get(...)`). The contract for `is_error` in
   `NormalizedEnvelope['tool_calls'][i]['is_error']` is therefore
   `bool | None` — with `None` meaning "no evidence the tool
   actually ran".

2. **`tools/fixtures/rung5-gate.py`** (line 81):
   The current failure condition is `if tc.get("is_error") is True`.
   That fails ONLY when `is_error` is strictly `True`. `None`
   passes through — the gate has no evidence the tool ran, but
   also no evidence it errored, so it counts as clean.

3. **`tools/adapters/factory.py`** (line ~113):
   `"is_error": bool(envelope.get("is_error"))` captures the
   run-level error flag into the normalized envelope. None of
   rung3, rung5, or rung6 read this field. An aborted/errored
   run greenses if tools + prose look right.

### Repro (hand-validated by Codex + Grok + backstop)

Inputs (committed in `tools/fixtures/rung7b-fakepass/`,
unit B of this branch):

- **`fake-envelope.json`** (verbatim fields):
  - `session_id`        : "fakepass-session-uuid"
  - `num_turns`         : 2         (>0)
  - `duration_ms`       : 9000
  - `is_error`          : false     (the gate never checks this)
  - `usage.input_tokens`: 8000      (>0)
  - `usage.output_tokens`: 420      (>0)
  - `usage.cache_read_input_tokens`: 0
  - `usage.thinking_tokens`: 160
  - `result`            : "## Verdict: REJECT\n\n## Finding: doubled charset\n... Content-Type: text/plain; charset=utf-8; charset=utf-8"
- **`fake-session.jsonl`** (single assistant message): one `tool_use`
  event with `name=Read`, `args.file_path=<validator_cwd>/api/llms_txt.py`,
  `id=toolu_fakeid_01`. NO matching `tool_result` event → `is_error=None`.

What the gates did (pre-fix, recorded in unit B as the
**valid-RED baseline**):

- rung 3 LIVE : GREEN — num_turns=2, tool_calls_total=1, tokens>0,
                tool name "Read" in allowlist.
- rung 5 LIVE : GREEN — no `is_error is True` violation; the lone
                Read on api/llms_txt.py satisfies required-source-
                coverage.
- rung 6 LIVE : GREEN — `## Verdict: REJECT` matches decision regex;
                `charset=utf-8; charset=utf-8` matches finding regex.

This is the silent-green the project exists to kill: zero real
validation, full green ladder.

### Confirmed by

- Codex validator on this fixture (orchestrator's blind MEASUREMENT
  run, captured in unit D ledger rows; raw envelope not committed).
- Grok validator on this fixture (same).
- This runner's hand-reproduction (committed fixture under
  `tools/fixtures/rung7b-fakepass/`; gate outputs in unit B commit
  message with exit codes checked WITHOUT pipes).

### Fixes (scheduled)

Two changes are required (rung 5.5 unit C, single commit):

1. `tools/fixtures/rung5-gate.py` — change the failure condition
   so a tool_use that is NOT provably clean fails. New condition:
   `if tc.get("is_error") is not False` → fail (covers `True` and
   `None`). An unpaired/unresolved tool_use has no evidence of
   execution; it is NOT clean.

2. After normalizing, every gate must thread-check
   `envelope.is_error`. If `True`, the gate fails regardless of
   tools/prose. The three gates all import the same adapter, so
   the check goes into each gate's leading assertions.

Outcome verified in unit C commit message: the rung7b fixture
exits non-zero on all three gates; the LIVE matrix (LIVE=GGG,
Config A=GGR, Config B=RRR) is UNBROKEN.

---

## Filing instructions (forward)

Add new issues under this file with the schema:

```
## Issue: <short name>

- **Status:** confirmed | observed | suspected
- **Surface:** rung N, <axis>
- **Filed:** YYYY-MM-DD
```

and a **Repro / Root cause / Candidate fixes / Why OUT OF SCOPE now**
block. Do not auto-fix; rung-X+ work needs orchestrator sign-off.

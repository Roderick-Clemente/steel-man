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

---

# Run r-quantum-404 (2026-08-16) — first live end-to-end sprint-loop run

Five defects surfaced by the first real `sprint-loop.py` run (pilot:
QuantumBank content-negotiated 404). Evidence: `evidence/runs/r-quantum-404-20260816/`.

## Issue KI-1: Planner per-call 600s timeout when no pilot spec is wired

- **Status:** FIXED (this run). Was: run-blocking.
- **Surface:** `tools/sprint-loop.py` `run_planner`; `sprint_loop/droid.py` `invoke_droid` 600s per-call cap.
- **Filed:** 2026-08-16.

### Symptom
With `pilot_spec_file` unset, the planner prompt carried `(no --pilot-spec-file)` as
its truth source. Under `--auto medium` with `Execute` on the large framework repo the
planner explored for context and exceeded the 600s cap; the run aborted with
`subprocess.TimeoutExpired` before writing `plan.md`.

### Repro
Run with `config.json` `pilot_spec_file: ""`; the `claude-opus-5` planner call exceeds
599.99s and raises `TimeoutExpired`.

### Fix
Wrote an implementation-free `pilot-spec.md` and set `pilot_spec_file`. Planner then
completed in ~330s. Root cause is the missing spec, not the cap.

## Issue KI-2: Executor tool allowlist names tools absent from droid 0.180

- **Status:** FIXED (commit `34b3272`). Was: run-blocking.
- **Surface:** `tools/sprint-loop.py` `main()` role assembly (executor + test-designer `enabled_tools`).
- **Filed:** 2026-08-16.

### Symptom
`enabled_tools` was `Read,Glob,Grep,LS,Edit,Create,ApplyPatch,MultiEdit,Execute`. droid
0.180's registry has no `ApplyPatch` or `MultiEdit`; `droid exec` rejected the list with
`Unknown tool identifier(s)` and wrote a 0-byte envelope, which then cascaded into the
§17.2 family guard reporting `family='unknown'` post-resolution.

### Repro
`droid exec --model glm-5.2 --list-tools` — `ApplyPatch`/`MultiEdit` absent;
`Read,Glob,Grep,LS,Edit,Create,Execute` present. Passing the missing ids reproduces the
empty envelope.

### Root cause
The framework hard-codes an editor set (PRD §1054 + a unit test) assuming an older tool
registry. Narrowed to the valid set; this pilot installs no locked-test guard hook, so
`Edit,Create,Execute` suffice.

## Issue KI-3: Audit commit crashes when evidence_output_dir is outside framework_root

- **Status:** OPEN. Severity: run-blocking for split-repo layouts.
- **Surface:** `tools/sprint-loop.py` `commit_chunk_change` (the `[H-9]` branch).
- **Filed:** 2026-08-16.

### Symptom
`commit_chunk_change` commits only into `framework_root` and stages the evidence tree.
With `evidence_output_dir` outside the framework repo (the supported `[H-9]` per-pilot
overlay pattern) nothing is staged, so `git commit` fails with empty stderr ("nothing to
commit"). The full loop had already succeeded (executor GREEN, both validators
ACCEPT-WITH-NITS); only this final bookkeeping step crashed.

### Repro
Set `evidence_output_dir` outside `framework_root`; run to chunk commit. `_git("commit",
...)` raises `RuntimeError: git ('commit', ...) failed:` with empty stderr.

### Fix direction (not applied)
Either (a) point `evidence_output_dir` inside `framework_root`, or (b) skip the commit
when `stage_paths` is empty instead of calling `git commit` unconditionally.

## Issue KI-4: Gate drops a HIGH plan-review finding from its own ledger

- **Status:** OPEN. Severity: silent-green class (defeats the §5.3 precondition).
- **Surface:** plan-review finding aggregation -> `findings.jsonl` + reconcile packet; §5.3 check.
- **Filed:** 2026-08-16.

### Symptom
Plan reviewer grok-4.5 returned REJECT with a HIGH finding (F-3a91c2: hard constraints
promoted in the plan never reach `chunks.json`, the only doc the runner feeds
executor/validator). That HIGH finding appears in neither `findings.jsonl` (only
medium/low rows) nor the reconcile packet. The §5.3 auto-accept precondition (">=1
APPROVE bound + no open blocker/high") therefore passed vacuously and the plan
auto-accepted on 1/2 APPROVE. The framework built to catch silent-green silently dropped
its own reviewer's most severe silent-green objection.

### Repro
Compare grok's raw envelope (`evidence/plan-reviewer-1-envelope.json`, 6 findings incl.
F-3a91c2 severity=high) against `telemetry/findings.jsonl` (5 grok rows, all medium/low;
F-3a91c2 absent) and `evidence/reconcile-packet.txt` (no HIGH). The dropped block is the
first JSON object in the envelope, preceded by a prose preamble and a `---` rule.

### Root cause (suspected)
The finding parser misses the first fenced JSON block when it follows prose/heading and a
horizontal rule. Net effect: severity that should gate the run never enters the ledger the
gate reads.

## Issue KI-5: Plans leak implementation, defeating independent-executor claims (§13)

- **Status:** OPEN. Severity: invariant erosion (third recorded instance).
- **Surface:** planning stage (`plan.md` authored by the planner seat); `plan-lint.py` coverage gap.
- **Filed:** 2026-08-16.

### Symptom
`plan.md` named both the discriminator (`startswith('/api/')`) and the response helper
(`jsonify`) — implementation choices, not observable behaviour — despite asserting it "does
not prescribe how the branch is implemented." The executor's fix reproduces exactly those
choices, so this run cannot support an independent-implementation (H3) claim. Filed against
the planning stage, not the executor: the executor did what it was told; the plan told it
too much.

### Repro
`grep -niE 'startswith|jsonify|request\.path' evidence/plan.md` -> §7 C6 names the
`startswith('/api/')` boundary and the `jsonify({"error": ...})` convention.

### Root cause
Writing a plan naturally pulls the author toward the solution already in mind; this is a
systemic property, not carelessness. Phase 4 records the same §13 failure for Phases 1 and
3 — three instances now. Per OPERATING-RULES, a rule that relies on remembering is not a
rule.

### Recommendation (deterministic-tier fix; not applied here)
Extend `plan-lint.py` to flag implementation-prescriptive language in chunk specs and plan
behavioural criteria: method names, library/helper calls, and function names appearing
where only observable outcomes belong are a smell. A mechanical check catches a class the
human + panel have now missed three runs running.

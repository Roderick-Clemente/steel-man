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

- **Status:** FIXED 2026-08-16 (`factory/ki3-empty-stage-commit`). Severity: run-blocking for split-repo layouts.
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

### Fix
Direction (b): skip the audit commit when `stage_paths` is empty, with a loud stderr
notice pointing at the `[H-9]` warning. Direction (a) (move the evidence dir inside
`framework_root`) was rejected — it papers over the crash and breaks the supported
`[H-9]` per-pilot overlay pattern. Regression tests pin both sides: outside-root skips
without any `git commit`, inside-root still stages and commits.

## Issue KI-4: Gate drops a HIGH plan-review finding from its own ledger

- **Status:** FIXED 2026-08-16 (`factory/ki4-finding-parser`). Severity: silent-green class (defeats the §5.3 precondition).
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

### Root cause (confirmed)
Not the prose/`---` preamble as first suspected. `_parse_finding_block`'s regex DID match
all 6 blocks; the naive brace counter that followed desynced on an unbalanced `{` inside a
JSON string value — F-3a91c2's evidence array quotes the template literal
`validator receives {{chunk_spec}` — so the balance never returned to zero and the block
was silently skipped. Net effect: severity that should gate the run never entered the
ledger the gate reads.

### Fix
Replaced the brace counter with string-aware `json.JSONDecoder.raw_decode`, anchored on
each `"finding_id"` occurrence (walking back to the enclosing `{`). Regression tests pin
grok's real envelope as a committed fixture (`tools/fixtures/ki4-dropped-high/`, same
pattern as `rung7b-fakepass`): all 6 findings parse, F-3a91c2 present with severity=high,
plus a synthetic unbalanced-brace repro. Fixed by hand, not through the loop: the loop's
auto-accept precondition was the thing broken.

## Issue KI-5: Specs and plans leak implementation, defeating independent-executor claims (§13)

- **Status:** OPEN. Severity: invariant erosion (third recorded instance).
  Rewritten 2026-08-16: originally filed against the planning stage alone; this run
  leaked at two layers with distinct authorship (spec-originated `jsonify`,
  plan-originated `startswith`).
- **Surface:** pilot-spec authorship (`pilot-spec.md`) AND plan authorship
  (`plan.md`), both propagating to the executor; `plan-lint.py` coverage gap at
  BOTH layers.
- **Filed:** 2026-08-16.

### Symptom
Two leaks with two distinct roots, both reproduced verbatim by the executor
(`jsonify({"error": "Not found"}), 404`), so this run cannot support an
independent-implementation (H3) claim:

1. **`jsonify` — spec-originated.** The chain is **spec -> plan -> executor**.
   `pilot-spec.md` line 8 reads "see `api/api_endpoints.py`, which returns
   `jsonify({"error": ...}), <code>` for its own error cases"; `plan.md` line 95
   reproduces that helper. The planner did what the spec primed it to do.
2. **`startswith('/api/')` — plan-originated.** The chain is **plan -> executor**.
   The spec states the `/api/*` boundary only observably; constraint C6
   (`plan.md` line 147, promoted from review-round-1 finding `F-b19c55`) both
   states the binding rule ("a request is 'API' iff its path begins with `/api/`",
   which is observable) and then proves it with a string-method diagnostic
   (`'/apiary'.startswith('/api')` is True while `'/apiary'.startswith('/api/')`
   is False) — naming the implementation the executor then used.

In both cases the leaking document asserts it "does not prescribe how the branch is
implemented." The executor did what the plan told it; the plan leaked at two layers
with different authorship.

### Repro
`grep -niE 'jsonify|api_endpoints' pilot-spec.md` -> line 8 names the
`jsonify({"error": ...}), <code>` convention (spec-originated leak).
`grep -niE 'startswith|jsonify|request\.path' evidence/plan.md` -> line 95 repeats
the `jsonify` convention (propagated from spec); line 147 (constraint C6) adds the
`startswith('/api/')` diagnostic (plan-originated leak; absent from the spec).

### Root cause
Writing a spec or plan naturally pulls the author toward the solution already in mind;
this is a systemic property, not carelessness. Phase 4 records the same §13 failure for
Phases 1 and 3 — three instances now. Per OPERATING-RULES, a rule that relies on
remembering is not a rule. The original filing repeated the same mistake at the meta
level: it blamed the layer nearest the symptom (the plan) for the `jsonify` leak that
the spec authored, and its proposed `plan-lint` rule scanned only chunk specs — it
would not have caught either leak. The `startswith` leak, by contrast, genuinely is
plan-authored: attributing both to the spec would overclaim, and each layer needs its
own guard.

### Recommendation (deterministic-tier fix; not applied here)
Extend `plan-lint.py` to flag implementation-prescriptive language in **pilot specs AND
plans** (both layers, not chunk specs alone): method names, library/helper calls
(`jsonify`), string-method discriminators (`startswith`), and function/file references
appearing where only observable outcomes belong are a smell. A mechanical check catches
a class the human + panel have now missed three runs running — and the lint must run at
spec-intake time, before the leak can propagate down the chain.

---

# Session-separated executor seat (2026-09-11)

## Issue KI-6: A harness subagent cannot hold a cross-family executor seat

- **Status:** confirmed (droid 0.197.0). Design direction withdrawn, not deferred.
- **Surface:** proposed `executor_backend: "subagent" | "droid_exec"` config key (never built).
- **Filed:** 2026-09-11.

### Motivation for the proposal
§22 ("author is not the verifier") keeps being violated the same way in
unattended runs: one agent session collapses the builder, orchestrator,
validator and referee roles — it writes the implementation itself instead of
letting the executor seat run, then fires the validators of its own code.
`--force-accept` addresses the §5.3 gate but not the identity problem. The
proposal was to spawn the executor as a harness **Task subagent** (separate
session, separate context) so §22 separation comes from the architecture
rather than from a new rule, per the operator's standing constraint of no new
hard rules.

### Why it does not work
A Task subagent inherits the **parent session's model** unless the harness has
per-tier model routing configured; there is no per-call model argument. So the
subagent executor is always the orchestrating agent's own family. That is
strictly worse than the status quo on two counts:

1. It puts the same family in the spec/orchestrator seat and the
   implementation seat, which is the §17.2 collision the family guard exists
   to refuse.
2. It forecloses the H3 hypothesis (cheap cross-family executors can do the
   work), because the seat can no longer be pinned to a cheap model.

`droid exec --model <id>` already provides a separate process, separate
session and separate context, and it *can* be pinned. The recurring §22
violation was never caused by `droid exec`; it was caused by agents skipping
the runner entirely and hand-coding — a behaviour the KI-2 tool-identifier
defect made rational, since the executor seat could not start at all.

### Resolution
No `executor_backend` key. The executor seat stays `droid exec` with a pinned
cross-family model. Revisit only if the harness exposes per-subagent model
selection; at that point the subagent path would add session-identity
separation *on top of* family separation rather than trading one for the
other.

## Issue KI-7: Planner seat is told to write a file it has no tool to write

- **Status:** FIXED (pending commit). Was: run-blocking, and it wasted two reviewer calls per run.
- **Surface:** `tools/sprint_loop/prompts/planner.md` `## Output`; `tools/sprint-loop.py` `run_planner`.
- **Filed:** 2026-09-11.

### Symptom
The persisted `plan.md` was a seven-line chat summary claiming a complete plan had
been written. Both cross-family plan reviewers rejected it (13 and 12 findings, all
citing unsupported self-claims); the §5.3 gate refused with exit 4. No executor call,
no code written.

### Root cause
Two independent defects compounding.

1. The planner seat runs with `enabled_tools = "Read,Glob,Grep,LS,Execute"` — no
   file-writing tool — while its prompt instructed it to produce "a single markdown
   document at `{{plan_output_path}}`". Having no write tool, the seat improvised a
   shell write: `python3 -c "import os, base64; ...write(base64.b64decode('<blob>'))"`.
   The blob was mangled in transit and the command died with
   `SyntaxError: unmatched ')'`. The planner reported success anyway.
2. `run_planner` never read that path. It took `envelope["result"]` as the plan,
   wrote it over `plan_doc_path` and hashed it into `plan_sha256`, with no check that
   the text was a plan. Two writers contended for one path and the loser's content
   was the real work.

The eight-section plan the planner actually composed (~8.5KB) survived only inside the
arguments of the failed command, recoverable from the seat's session transcript.

### Repro
Give any read-only seat a prompt that names an output path, and accept
`envelope["result"]` as the artifact. The seat's shell write can fail while its final
message still claims success.

### Fix
The prompt now asks the planner to emit the document as its final message, and states
that the runner persists it — one writer, and no seat is asked for a capability it was
not granted. `run_planner` validates the text structurally before hashing
(`_validate_plan_document`) and refuses a document missing the required sections, or
one that reads as a report about a plan rather than a plan. The planner seat was
deliberately **not** given a write tool: a planning seat with repo write access is a
worse trade than a validated envelope result.

### Generalisation (check before adding any seat)
`seat_outcome="ok"` means the seat returned a parseable envelope, not that it did its
job; it cannot detect this failure by construction. Any seat whose prompt names an
output path but whose `enabled_tools` lacks a write tool has this defect shape. The
plan reviewer and validator seats are also read-only-plus-`Execute`: if a future
prompt asks them to write a report to a path, expect the same silent green. The
durable guard is to validate the artifact's content, not the seat's exit code (§7).

## Issue KI-8: The planner never sees the authored chunk contract

- **Status:** FIXED (pending commit). Was: wasted a full cross-family review pass per run.
- **Surface:** `tools/sprint-loop.py` `run_planner` prompt context; `tools/sprint_loop/prompts/planner.md` `## Inputs`.
- **Filed:** 2026-09-11.

### Symptom
Sixteen blocker/high plan-review findings, about half of them faulting chunk
boundaries, file paths and locked-test directories that do not exist and would never
have executed. The gate refused with exit 4. The operator's authored chunk contract
was correct throughout.

### Root cause
`run_planner` renders the planner prompt with `pilot_spec_path` and
`plan_output_path` only. `--chunks-file` is never passed, so a planner asked for a
"Chunk plan" section invents one from the pilot spec alone. Execution is driven
entirely by the authored chunks JSON. Two sources of truth for chunking, only one of
which runs, and the reviewers audit the one that does not.

The invented chunking is confidently wrong in the way an unconstrained model is
always wrong about a repository it has only read a spec for: it named plausible
frontend paths that did not exist and a locked-test directory the pilot does not use.

### Repro
Author a chunks file, run the planner, and diff the plan's chunk section against the
chunks file. The chunk ids, allowed files and locked tests will not match.

### Fix
When a chunks file is supplied, `run_planner` renders it into the prompt and the
planner must reproduce its ids, allowed files, locked tests and commands exactly.
Its job shifts from inventing a chunking to **reconciling the contract against the
pilot spec** — reporting, under Open questions, any spec rule no chunk covers, any
chunk criterion with no basis in the spec, and any contradiction between the two.
When no chunks file is supplied the planner proposes a chunking as before; both flows
are legitimate.

### Note
This converts the most expensive seat pair in the loop from auditing a fiction into
performing the one review the operator cannot do alone: whether the locked contract
actually covers the spec. The remaining findings from the observed run were genuine
and concerned the plan contradicting numbered spec rules — those are the findings the
pass exists to produce.

## Issue KI-9: RED classifier rejects a valid RED for explaining itself

- **Status:** FIXED (pending commit). Was: run-blocking for any chunk introducing a new module.
- **Surface:** `tools/phase-1-scripts/valid-red.py` `classify()` / `INVALID_RED_SIGNATURES`.
- **Filed:** 2026-09-11.

### Symptom
A seven-test locked file failed correctly — `collected 7 items`, seven `FAILED`, exit
code 1, each failure an `AssertionError` raised at a real assertion in the test body.
The classifier returned `{"valid": false, "reason": "Invalid RED: missing module
import"}`. The chunk bounced back to the test designer, regenerated, failed
identically, and the run paused without the executor ever being called.

### Root cause
`classify()` regex-matches `INVALID_RED_SIGNATURES` against the entire combined
stdout+stderr *before* examining any structural evidence. The test under examination
imported the not-yet-existing module inside a guard and put the captured cause in its
assertion message:

```
E   AssertionError: <marker>: <module> must exist (import failed:
    ModuleNotFoundError: No module named '<module>')
```

The substring `ModuleNotFoundError:` therefore appeared in the output, and the
classifier could not tell "the test file failed to import" from "the test executed,
reached its assertion, and the message quotes an import error".

Text matching over pytest output cannot separate those two. The distinguishing
evidence is structural and was already present: a file that truly cannot be imported
produces a collection ERROR and **zero executed tests**, while this run collected and
executed seven.

The same false-positive shape affects other entries in the list: `conftest\.py`
matches if that filename appears anywhere in a traceback, and `assert\s+True\b`
matches if pytest's source context merely displays such a line.

### Perverse incentive
Because the guard penalised the assertion *message*, the only way past it was for a
RED test to say nothing about why it was red. The framework was rewarding less
informative tests — the opposite of §7.

### Fix
Classify on structure first (collected count, collection ERROR vs executed FAILED,
exit code), then apply text signatures only where they are meaningful.
Collection-phase signatures (import, syntax, fixture, conftest, empty selection) are
consulted when the structure shows a collection or execution failure, or when matched
outside the `FAILURES` region. Test-quality signatures (tautological assertion, mocked
subject) still invalidate an executed failure, since they mean the test asserts
nothing real, but are scoped to assertion lines rather than the whole blob.

### Note
The guard's purpose is unchanged and still enforced: a test file that cannot be
imported is still an invalid RED, and so is a tautological or mocked-subject test.
What changed is that the evidence used to decide is structural rather than
lexical.

## Issue KI-10: The validator seat runs on an unrendered prompt template

- **Status:** FIXED (pending commit). Was: blocker — every validator verdict through this path was unsound.
- **Surface:** `tools/sprint_loop/per_chunk.py` `run_validators`; `tools/sprint_loop/backends.py` `LocalBackend`; `tools/orchestrate-review.py` `--prompt-file`.
- **Filed:** 2026-09-11.

### Symptom
Two validator seats reviewed the same chunk and disagreed about what they were even
looking at. One reconstructed its inputs and produced a real review; the other refused
to review anything.

### Root cause
`prompts/validator.md` carries six placeholders — `{{branch}}`, `{{chunk_spec}}`,
`{{commit}}`, `{{evidence_bundle_path}}`, `{{pilot_root}}`, `{{test_file_path}}`.
`run_validators` passes the template **path** as `prompt_template_path`;
`LocalBackend` forwards it to `orchestrate-review.py` as `--prompt-file`, which
resolves it to an absolute path and hands it to `droid exec` verbatim. Nothing
substitutes the placeholders anywhere in that chain — `orchestrate-review.py` contains
no substitution logic at all. The planner, test-designer and executor seats all go
through `render_to_file`; the validator seat was the one that never did.

### Observed
- `grok-4.5` opened its report with "Inputs used (recovered; prompt placeholders were
  unsubstituted)", rebuilt the chunk spec, commit, locked test path and bundle path by
  inspecting the repository, and then produced a genuine and useful review that found
  a real unlocked criterion.
- `gemini-3.1-pro-preview` refused: "The provided prompt is an unrendered template
  rather than an actionable validation context ... Without the actual spec, diff, and
  evidence bundle, no validation can be performed."

The two verdicts (`REJECT_TEST` and `REJECT_IMPLEMENTATION`) were therefore not
independent judgements of the same artifact. One was a review; the other was a
complaint about the harness, wearing a verdict label that pointed at the
implementation.

### Why it went unnoticed
A capable validator compensates. The seat still returns a well-formed envelope with a
parseable verdict, so `seat_outcome` is `ok`, the telemetry row looks healthy, and the
gate counts the verdict. Nothing downstream distinguishes "reviewed the code" from
"reverse-engineered the inputs then reviewed the code" or from "could not review at
all". The failure is only visible if a human reads the report prose.

### Fix
Render `validator.md` through `render_to_file` with real values, write the rendered
prompt into the chunk evidence directory so it is archived alongside every other
seat's prompt, and refuse to invoke when any `{{placeholder}}` survives rendering. A
validator running blind must be a loud failure, not a silent one.

### Generalisation
Grep for every seat invocation that passes a template path rather than a rendered
file. The lesson repeats KI-7's: a seat given inputs it cannot use will often produce
something that *looks* like output, and the framework's own success signals will not
tell the difference. Assert on the artifact.

## Issue KI-11: The chunk's full-suite regression command was never run

- **Status:** FIXED (pending commit). Was: blocker — the regression gate did not exist.
- **Surface:** `tools/sprint-loop.py` `run_chunk_inner` → `per_chunk.produce_evidence`; `tools/phase-3.2-evidence/local_backend.py` `--full-suite`.
- **Filed:** 2026-09-11.

### Symptom
A validator reported that the evidence bundle proved only the locked test:

```
tests.passed = 8    tests.failed = 0    tests.suite_exit_code = 0
```

while the chunk's own contract named two commands — the locked test *and* a
full-suite regression run. The chunk criterion "existing behaviour unchanged" was
therefore unevidenced, and the validator correctly refused to substitute the
executor's prose claim of "37 passed" for proof.

### Root cause
Two independent gaps in the same path.

1. `tools/phase-1-scripts/verify-green.py` runs only the locked test, by design.
   The regression suite is the bundle producer's job, behind `--full-suite`.
   `per_chunk.produce_evidence` already forwarded that flag — but
   `sprint-loop.py` never passed it. So no runner-driven sprint has ever executed a
   chunk's full-suite command. The second command in every chunk contract was
   decorative.
2. When the flag *was* passed by hand, the producer overwrote the locked-test
   counters with the full-suite ones, so the two could not be distinguished. A
   validator reading `tests.passed` could not tell which suite it described.

### Fix
The runner now passes `--full-suite` when the chunk names a regression command
distinct from its locked test, and the producer records that result separately under
`tests.full_suite` with `tests.scope` markers on both, so a validator can never
confuse the locked test for the regression gate. `produce_evidence` fails closed if a
full suite was requested and the bundle comes back without it, and the consumer and
orchestrator gate fail closed on a red regression suite. The bundle schema change is
additive; older bundles still validate.

### Note
The executor's own summary had said "37 passed", and independent re-running confirmed
37 was true. That is exactly why the validator was right to reject it: the number
was correct and the evidence was absent, and a gate that accepts correct-sounding
prose will accept incorrect-sounding prose on the day it matters.

## Issue KI-12: Bundle producer does not import under Python 3.9 (by design)

- **Status:** NOT A BUG — documented limitation. Closed without code change.
- **Surface:** `tools/phase-3.2-evidence/local_backend.py` (PEP 604 annotation, no `from __future__ import annotations`).
- **Filed:** 2026-09-11. Reclassified 2026-09-12.

### Resolution
`README.md` states **"Requires Python 3.10+."** PEP 604 unions failing to import on
3.9 is therefore expected behaviour, not a defect, and
`tests/test_layout_paths_chunk2.py` is *correct* to assert that failure on
`sys.version_info < (3, 10)`. No change is warranted. Recorded here as a limitation
so the next agent that trips over it on a stock macOS `python3` does not
"fix" a working contract.

### Why this entry is kept rather than deleted
An agent (this one) hit the import error, wrote the one-line `__future__` fix,
and only then discovered that a judge test asserts the failure — and that the judge
is pinned byte-for-byte by
`tests/test_layout_paths_chunk3.py::test_chunk3_existing_judges_byte_unchanged`.
Both edits were reverted.

That is the lock working exactly as intended. The agent's next step would have been
to edit the judge and its pinned hash so the suite agreed with its own change, which
is the precise failure mode the byte-lock exists to prevent. The lesson generalises
beyond this file: when a test contradicts your change, the test is the contract until
a human says otherwise.

### Original report (retained for context)

#### Symptom
```
$ python3 -c "import local_backend"
TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'
  at: def run_coverage(pilot_root: str, test_file: str, python: str) -> dict | None:
```
The runner's own interpreter is 3.9.6. The module uses PEP 604 unions without
`from __future__ import annotations`, so it cannot be imported there at all. Every
other module in the tree carries that import.

#### Why it is not fatal
The producer is invoked with the pilot's interpreter, which on a supported 3.10+
pilot works fine — which is why live runs produce bundles. A 3.9 pilot is outside
the stated requirement.

## Issue KI-13: Unvalidated implementation is committed before the chunk gate

- **Status:** OPEN — design defect, fix not yet written.
- **Surface:** `tools/sprint_loop/prompts/executor.md` ("after you commit"); `tools/sprint-loop.py` `commit_chunk_change` call sites in the chunk loop.
- **Filed:** 2026-09-12.

### Symptom
A live run produced an implementation that went GREEN (locked test 8/8, full suite
37/37, every file inside `allowed_files`) and was then **rejected by validation**.
The rejecting finding was correct. But the implementation was already sitting on the
pilot's working branch as a normal commit, indistinguishable from reviewed work.

The operator had to reset the branch by hand to get unvalidated code off it.

### Root cause — two separate ordering problems

1. **The executor commits its own work.** `executor.md` tells the seat: *"The runner
   calls `tools/phase-1-scripts/verify-green.py` after you commit changes."* So the
   author seat commits before GREEN is even verified, let alone validated. The commit
   is the executor's own act, which means no gate stands between "a model wrote code"
   and "the branch contains that code".

2. **The runner commits on the not-accepted path too.** In the chunk loop:

   ```python
   if chunk.status != ChunkStatus.ACCEPTED:
       print(f"  chunk {chunk.chunk_id} did NOT accept; pausing")
       rs.status = RunStatus.AWAITING_HUMAN_DECISION
       write_checkpoint(...)
       commit_chunk_change(rs, chunk, chunk_evidence_dir, run_evidence_dir=evidence_dir)
       return 3
   ```

   `commit_chunk_change` is documented as *"One commit per accepted chunk on the
   output branch"* and is nonetheless called when the chunk did **not** accept. (This
   call targets the framework's own audit files rather than the pilot, so it is the
   lesser of the two problems — but the invariant it advertises is not the one it
   enforces.)

### Why this matters more than it looks
The framework's entire claim is that code does not land until independent
cross-family validation accepts it. Committing at GREEN inverts that: GREEN means
"the author satisfied the test the author was given", which is exactly the signal the
adversarial design treats as insufficient. An operator reading `git log` cannot tell
accepted work from rejected work, and the rejected commit is the *default* state of
the branch until someone intervenes.

It also interacts badly with KI-10: for as long as the validator seat ran on an
unrendered prompt, *every* chunk was landing on this path.

### Fix direction
Move the pilot-side commit to **after** the chunk gate accepts, not after tests pass.
Concretely: the executor should leave its work uncommitted (or on a scratch ref that
is never the working branch), verify-green and the validators should run against that
state, and only an ACCEPT should produce the commit on the working branch. A rejected
chunk should leave the branch exactly as it was found, with the work preserved as
evidence rather than as history.

Note the interaction with the §7 uncommitted-tree guard: the executor currently
commits partly so that later steps see a clean tree. Any fix has to give the
verify-green and validator steps a defined way to read uncommitted or
scratch-ref work, or the guard will simply block the new ordering.

### Workaround until fixed
Preserve the implementation on a ref before resetting, so nothing is lost:

```
git branch  chunk/<id>-<model>-unvalidated <sha>
git tag     evidence/<id>-<model>-green-unvalidated <sha>
git reset --hard <sha>^
```

## Issue KI-14: An invalid RED still retries the executor

- **Status:** PARTIALLY FIXED — implementation retries now recognize their
  expected GREEN starting state; first-attempt invalid RED classification
  remains a separate routing follow-up.
- **Surface:** `tools/sprint-loop.py` — the `RED_REJECTED` branches set `chunk.status` and `chunk.gate_decision` but never `chunk.rejection_kind`.
- **Filed:** 2026-09-12.

### Symptom
`REJECT_TEST` from the validation gate now routes to the test-designer on its own
bounded budget. `RED_REJECTED` does not: it sets

```python
chunk.status = ChunkStatus.RED_REJECTED
chunk.gate_decision = GateDecision.REJECT
chunk.gate_reason = rs.status_message
```

and leaves `rejection_kind` empty, so `run_chunk_with_retries` takes the generic
path and re-invokes the **executor**.

### Why that is the wrong seat
A test that will not go RED is a defective test, not defective code — the same
category as `REJECT_TEST`. There is by definition no implementation yet for the
executor to correct, so the retry cannot fix anything; it just spends the most
expensive seat in the pipeline to re-observe that the test is unusable.

### Fix direction
Set `rejection_kind = REJECTION_TEST` on the `RED_REJECTED` paths and let the
existing test-design budget carry it, reusing the routing added for the validation
gate rather than adding a third branch. The one distinction to preserve: a RED
failure caused by the *environment* (collection error, missing dependency) is
neither a test nor an implementation defect and should still stop for a human rather
than burn either budget — see the `ENVIRONMENT_SIGNATURES` split in
`tools/phase-1-scripts/valid-red.py` (KI-9).

### Partial fix
KI-16 exposed a narrower live failure with the same symptom. After
`REJECT_IMPLEMENTATION`, the locked test is necessarily GREEN because the
validator runs only after `verify_green`. The retry used to re-enter the RED
gate, classify that expected GREEN as `RED_REJECTED`, and spend its remaining
executor budget without ever invoking the executor. Implementation-directed
retry rounds now confirm the existing GREEN state and continue as a
verify-and-harden pass. A subprocess-backed regression test exercises the
real lock, RED, GREEN, and evidence gates across both rounds.

## Issue KI-15: The evidence bundle is produced twice, and the second one wins

- **Status:** FIXED (pending commit).
- **Surface:** `tools/orchestrate-review.py` `step1_produce_evidence`; `tools/sprint_loop/backends.py` `LocalBackend`; `tools/phase-3.2-evidence/local_backend.py` `--full-suite`.
- **Filed:** 2026-09-12.

### Symptom
Two validator seats, reading a fully rendered prompt for the first time (see KI-10),
both returned `REJECT_IMPLEMENTATION` for the same reason:

> Locked suite `passed=6, failed=0, suite_exit_code=0, scope=locked-test`.
> `tests.full_suite` **absent**. Chunk commands include a directory-wide pytest run.
> Per the validator contract, absent `tests.full_suite` means there is **no**
> independent regression evidence. Executor prose ("35/35") is not evidence.

The refusal was correct. The evidence really was missing, and the seats were right
not to credit the executor's own count.

### Root cause — three defects in one path

1. **Two producers.** `sprint-loop.py` calls `produce_evidence(...,
   full_suite=bool(chunk_full_suite_command(chunk)))`, which for the live chunk
   evaluates `True`, appends `--full-suite`, and even fails closed if the bundle
   comes back without `tests.full_suite`. That path is correct. But validation then
   runs `run_validators` → `LocalBackend` → `orchestrate-review.py`, whose
   `step1_produce_evidence` builds *its own* producer invocation and rewrites the
   bundle at the same output path. `orchestrate-review.py` declares and honours
   `--full-suite`; `LocalBackend` never passes it. So the correct bundle is silently
   overwritten by one with no regression evidence, and that is the one the validators
   read.

2. **Full-suite mode runs the wrong command.** `--full-suite` is implemented as bare
   `pytest` from the pilot root, ignoring the regression command the chunk declares.
   Against a pilot whose tests live in a subdirectory, the observed result was:

   ```
   locked test: passed=6 failed=0 skipped=0 exit=0
   [2b] Running full regression suite...
     full suite: passed=0 failed=0 skipped=0 exit=5
   ```

   Exit 5 is pytest's "no tests collected". The regression gate ran nothing.

3. **"No tests collected" counts as a pass.** The exit decision tests
   `failed == 0`, so a run that collected zero tests satisfies it. A vacuous
   regression run therefore reports success, in the producer and in the consumer
   gate alike.

### Why this is the KI-7 / KI-10 shape again
Each layer produced a well-formed artifact and reported success. The bundle parsed,
the counters were internally consistent, the exit code was 0, and `seat_outcome` was
`ok`. Only a validator reading the bundle against the chunk's declared commands could
see that the stronger claim was never tested. The framework's own success signals
cannot distinguish "the regression suite passed" from "the regression suite did not
run".

### Note on ordering
KI-11 fixed the runner's producer and was verified in isolation against a scratch
pilot. It did not fire end to end because of defect 1 above. The isolated
verification was real but insufficient: it tested the path the runner takes, not the
path the validators read from.

### Fix
The chunk's declared regression command is derived **once** in the runner and threaded
to both producers (`run_validators` → `LocalBackend.validate` →
`orchestrate-review.py --full-suite-command` → `local_backend.py`), so the two cannot
disagree. `orchestrate-review.py`'s produce step now also fails closed when a bundle
it produced under a full-suite request comes back without `tests.full_suite`,
mirroring the check the runner's producer already had — so neither producer can hand
a validator a bundle missing the section.

The producer runs the declared command rather than bare `pytest`, preserving its
targets and selectors and re-imposing only the reporting flags it must own to parse
results. A command that does not invoke pytest is refused outright rather than
silently downgraded.

"Collected nothing" is now a refusal, not a pass, in all three gates (producer,
validator consumer, orchestrator gate), with the exit code named: pytest exit 5 or a
zero total means the run proves nothing about existing behaviour, and exits 2/3/4
mean pytest did not complete. Bundles predating the section are not retroactively
failed.

Verified end to end against a throwaway pilot shaped like the real one (tests in a
subdirectory that bare `pytest` does not collect): the bare-flag fallback now exits 1
naming "collected no tests (pytest exit 5)" where it previously exited 0; the declared
command records real counts; breaking one unrelated test yields producer exit 1 and a
`FAIL_CLOSED` gate while the locked test stays green.

## Issue KI-16: The executor retries blind after an implementation rejection

- **Status:** FIXED.
- **Surface:** `tools/sprint_loop/prompts/executor.md` (no prior-rejection section); `tools/sprint-loop.py` (`chunk.rejection_feedback` set to the gate string and never rendered).
- **Filed:** 2026-09-12.

### Symptom
A validator rejected a chunk with a specific, correct and actionable finding: an
observable criterion required that a stored reference to a deleted entity be
*reported as such*, and the implementation silently substituted a fallback, so the
criterion was never met. The reviewer even quoted the implementation's own docstring
rewriting the criterion into a weaker one.

The runner classified this `REJECT_IMPLEMENTATION` and re-ran the executor, which is
the right seat. The retry then failed **identically**.

### Root cause
`prompts/executor.md` has no placeholder for a prior rejection, and
`chunk.rejection_feedback` is set to a one-line gate string that is never rendered
into the executor's prompt at all. So an implementation-directed retry re-runs the
most expensive seat in the pipeline with no knowledge of why the previous attempt was
refused. It is not a retry; it is the same dice roll at full cost.

### Why it was invisible
The retry is well-formed: the seat runs, produces a diff, goes GREEN against the
locked test, emits a valid envelope, and `seat_outcome` reads `ok`. The only symptom
is that the same criterion fails again, and nothing in the run's own signals
attributes that to a missing input.

The asymmetry makes it plain: the test-designer *was* given
`{{prior_test_rejection}}` when `REJECT_TEST` routing was added, fed by
`format_test_rejection_feedback`. The executor is the same problem, and was left
unfixed because nothing had exercised an implementation-directed retry end to end
until a validator finally produced a real finding — which required KI-10 and KI-15 to
be fixed first.

### Fix direction
Render the rejecting seats' own finding text into the executor's prompt, attributed
per model, clipped, and only for implementation-directed rejections. Feed only the
seats that rejected: in the observed run one validator ACCEPTed and one rejected, and
handing the executor an approval beside a refusal would be actively misleading.

### Generalisation
Fourth instance of the KI-7 shape (KI-7, KI-10, KI-15, KI-16): a seat is invoked
without an input it needs, produces a plausible artifact anyway, and every success
signal the framework owns reports normal. The pattern to grep for is a retry or
re-invocation path that does not carry forward the reason it was triggered.

### Follow-up: the retry was unreachable live
The initial feedback fix covered prompt rendering and retry routing with
stubbed deterministic gates, but a live implementation retry never reached
that prompt. `REJECT_IMPLEMENTATION` is emitted only after `verify_green`, so
the next round begins with the locked test GREEN. `validate_red` rejected that
state and the retry burned its budget at the RED gate.

The RED relaxation now includes implementation-directed retry rounds. It
still verifies that the test is genuinely GREEN before proceeding, then
re-invokes the executor in verify-and-harden mode with the rejecting
validator's finding. The regression test stubs only the droid-backed seats;
lock, RED validation, GREEN verification, evidence production, prompt
rendering, and retry control all execute through the real paths.

## Issue KI-17: Warnings summary misclassified as a collection failure

- **Status:** FIXED.
- **Surface:** `tools/phase-1-scripts/valid-red.py` `outside_failures_region()`.
- **Filed:** 2026-09-13.
- **Numbering:** KI-17 was unused when this review-cleanup pass was filed;
  entries 14 through 16 and KI-18 were already assigned on the branch this
  stack repackages.

### Symptom
An executed failing test with a pytest warnings summary that cited
`tests/conftest.py:5` was rejected as `Invalid RED: conftest error`.
The test had collected and reached its assertion; the warning was unrelated
to collection.

### Root cause
The structure-first fallback scanned all output outside the `FAILURES`
section for collection-phase signatures. Pytest prints warnings summaries
outside that section, so a file path in a deprecation warning matched the
`conftest\.py` signature.

### Fix
Exclude pytest's warnings-summary section from the fallback scan. The
regression fixture records the observed one-test failure and conftest warning,
and verifies that it remains a valid RED.

## Issue KI-18: Test-designer bounce does not re-lock the redesigned test

- **Status:** OPEN.
- **Surface:** `tools/sprint-loop.py` `run_chunk_with_retries`; `tools/sprint_loop/per_chunk.py` `lock_test`.
- **Filed:** 2026-09-13.

### Symptom
After a `REJECT_TEST` verdict routed the chunk to the test-designer, the test-designer
rewrote the locked test (7 → 20 tests). The executor re-ran against the new test and
produced GREEN. The validators then rejected with `REJECT_TEST` again — not because
of the code, but because `locked_test_sha_observed` in the bundle no longer matched
the lock manifest (`test_homes_store.py.lock.json`). The manifest still held the
pre-redesign SHA.

### Root cause
`lock_test()` is called once during the initial test-designer phase. When a
`REJECT_TEST` bounce triggers a test-designer rewrite, the runner replaces the test
file but does not re-lock it. The lock manifest becomes stale, and any validator that
cross-checks the bundle SHA against the manifest will refuse.

### Impact
A split validator verdict on process integrity, not code quality. One validator
caught the mismatch (grok-4.5: REJECT_TEST naming the SHA difference); the other
missed it (gemini-3.1-pro: ACCEPT). The gate fail-closed on the split. The executor's
code was accepted on its merits by both validators.

This is also an experiment-integrity issue: the "same locked tests" controlled constant
did not hold for the arm that experienced the bounce.

### Fix direction
After a test-designer rewrite is accepted and the new test is written to disk,
`lock_test()` must be re-invoked to regenerate the lock manifest with the new SHA.
The re-lock should happen in `run_chunk_with_retries` after the test-designer
completes its redesign round, before the executor re-runs.

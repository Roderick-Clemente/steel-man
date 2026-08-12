# H3 Validation Analysis

## Hypothesis

A cheap-tier executor can implement a bounded chunk without being handed the
exact fix — the prompt describes the problem, not the solution. This is the
primary cost-saving mechanism of the sprint method (expensive planning +
cheap execution).

## Problem with Phase 3

In Phase 3, the executor prompt for chunk 1 contained the exact solution:
the full code for `PROFILE_DEMO_ADDRESS` and `get_user_profile`, including
the SQL query, the `_row_to_dict` call, and the address key assignment. The
executor's job was mechanical — paste the code, run pytest, confirm GREEN.
This means Phase 3 did **not** actually test H3. The cost thesis depends on
cheap executors being able to implement from a **spec**, not from a
**solution**.

## Design

| Parameter | Value |
|---|---|
| Chunk | Profile read model (`get_user_profile` in `models.py`) |
| Executor model | gpt-5.4-mini (cheap tier, OpenAI) |
| Executor auto level | medium |
| Prompt type | Un-hinted: describes the problem (behavioral spec), NOT the fix |
| Test | Same locked test from Phase 1 (`test/test_profile_model.py`, SHA-256 `8041e607...`) |
| Isolation | Git worktree at commit `0b871fb5` (test exists, implementation does not) |
| Validators | grok-4.5 (xAI) + gemini-3.1-pro-preview (Google) — cross-family |
| Validator evidence | In-session (validators run pytest themselves) |

### What the un-hinted prompt said (and did NOT say)

**Said:**
- "Return a dict with exactly four keys: username, email, full_name, address"
- "Select only display-safe columns by name. Fields like id, created_at,
  password_hash must not appear"
- "Address from a module-level configuration constant that supports an
  environment variable override with a sensible default"
- "Follow the same database access pattern used by similar functions"
- "Return None for unknown user"

**Did NOT say:**
- The exact SQL query (`SELECT username, email, full_name FROM users WHERE id = ?`)
- The constant name (`PROFILE_DEMO_ADDRESS` — the executor chose `PROFILE_ADDRESS`)
- The default value (the executor chose `"123 Demo Street, Springfield, IL 62704"`)
- The implementation pattern (`_row_to_dict` + add address key — the executor
  used explicit key mapping)
- Any code examples

## Results

### Executor

| Metric | Value |
|---|---|
| Model | gpt-5.4-mini (cheap tier) |
| Turns | 15 |
| Input tokens | 24,786 |
| Output tokens | 3,588 |
| Total tokens | 28,374 |
| Duration | 58 seconds |
| Tool errors (self-corrected) | 2 (1 ApplyPatch, 1 Execute) |
| External retries needed | 0 |
| GREEN achieved | Yes — on first attempt (no external retry) |

The executor had 2 tool-call errors (one ApplyPatch that failed, one Execute
that failed), both self-corrected within the same session. No external retry
was needed — the executor recovered on its own.

### Implementation quality

The executor's implementation was correct and clean:

- **Named columns only:** `SELECT username, email, full_name FROM users WHERE
  id = ?` — no `SELECT *`, no `id`, no `created_at`.
- **Config constant:** `PROFILE_ADDRESS = os.environ.get(PROFILE_ADDRESS_ENV,
  "123 Demo Street, Springfield, IL 62704")` with env override and TODO.
- **None handling:** `if user is None: return None`
- **Connection pattern:** Same as `get_user_by_username` — `get_db()`,
  `cursor()`, `execute`, `fetchone`, `close()`.
- **Scope:** Only `models.py` modified (31 lines, 0 deletions).

The executor made different naming choices than the Phase 3 implementation
(`PROFILE_ADDRESS` vs `PROFILE_DEMO_ADDRESS`, realistic address vs Picard
address), which confirms it was implementing from the spec, not reproducing
a memorized solution.

### GREEN verification (§7 — assert on reality)

| Check | Result |
|---|---|
| Locked test (3 tests) | 3/3 passed |
| Full regression suite | 89/89 passed |
| Method | Independent `pytest` run, not exit code |

### Cross-family validation

| Validator | Verdict | Input tokens | Output tokens | Duration |
|---|---|---|---|---|
| grok-4.5 (xAI) | ACCEPT | 16,151 | 1,545 | ~3 min |
| gemini-3.1-pro-preview (Google) | ACCEPT | 74,142 | 2,709 | ~2 min |
| **Gate** | **ACCEPT** | | | |

Both validators independently confirmed:
- Scope is clean (only `models.py` modified)
- Named columns (no `SELECT *`)
- None handling correct
- Config constant with env override and TODO
- Tests pass (they ran pytest themselves)
- No stray writes

## What this says about the cost thesis

**H3 is consistent with this run. N=1 — this is a single existence proof, not
support for the hypothesis.** One cheap-tier executor (gpt-5.4-mini) implemented
one bounded chunk from an un-hinted behavioral spec on one attempt. That
establishes the outcome is *possible*; it says nothing about how often it
happens, on which chunk difficulties, or with which models. Treat every
statement below as a description of this run:

1. **It can implement from spec:** The executor produced a correct, clean
   implementation without being handed the exact fix. It chose its own
   constant names, default values, and implementation pattern — all within
   the spec's constraints.

2. **It is cheap:** 28,374 total tokens and 58 seconds for a complete
   implementation including self-verification (pytest). This is the cheap
   execution seat that the sprint method's cost thesis depends on.

3. **It self-corrects:** The executor had 2 tool errors but recovered
   within the same session — no external retry needed. This is important
   because PRD §14 notes that "a cheap executor that needs three attempts is
   not cheap." This executor needed zero external retries.

4. **Validation holds:** Cross-family validators (grok + gemini) both
   ACCEPT'd the implementation. The validators saw the spec, the diff, and
   the test evidence — not the executor's reasoning.

### Caveats

1. **Small chunk:** The profile read model is a single function (~30 lines).
   Larger chunks with more complex logic may challenge a cheap executor more.

2. **`--auto medium` required:** The executor failed at `--auto low`
   ("insufficient permission to proceed"). This is a platform behavior note —
   the executor needs at least medium autonomy to edit files and run tests.
   This does not affect the cost thesis but is an operational constraint.

3. **ApplyPatch, not Edit:** gpt-5.4-mini uses `ApplyPatch` instead of `Edit`.
   The orchestrator and prompts should account for this tool name difference.

4. **One chunk, one model:** H3 was tested with one chunk and one cheap model
   (gpt-5.4-mini). Broader generalization would require testing more chunks
   and additional cheap models (e.g., glm-5.2).

## Conclusion

**N=1. Directional, not established.** One cheap-tier executor implemented from a
spec without being handed the exact fix, on one chunk. The cost-saving mechanism
(expensive planning + cheap execution) is therefore *not ruled out* and is worth
measuring properly. It is not yet demonstrated: a single success cannot separate
"cheap executors can do this" from "this chunk was easy." The executor produced correct code at
low token cost (28k tokens, 58 seconds) with zero external retries, and
cross-family validators confirmed the implementation meets the spec.

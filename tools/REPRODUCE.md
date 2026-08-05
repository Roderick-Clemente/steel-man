# tools/REPRODUCE.md — reproduce the seam-refactor behavior-preservation proof

This page tells an independent reviewer how to verify, from
scratch on a fresh clone of `factory/build-gate-tools`, that the
commit-below (Item 3 seam refactor) is **behavior-preserving**:
running the gates against the committed evidence reproduces the
verdicts recorded in `tools/RUN-LEDGER.md`.

## What's in the reproduction bundle

`tools/fixtures/evidence/`:

| file                     | size    | role                                    |
|--------------------------|---------|-----------------------------------------|
| `rung3-envelope.json`    | 727 B   | droid exec envelope for rung 3 LIVE     |
| `rung3-session.jsonl`    | ~57 KB  | inner-session jsonl for rung 3 LIVE     |
| `rung7A-envelope.json`   | 564 B   | droid exec envelope for rung 7 Config A |
| `rung7A-session.jsonl`   | ~95 KB  | inner-session jsonl for rung 7 Config A |
| `rung7B-envelope.json`   | 406 B   | droid exec envelope for rung 7 Config B |
| `rung7B-session.jsonl`   | ~13 KB  | inner-session jsonl for rung 7 Config B |

Path sanitization (before committing these JSONLs):

- All `/private/tmp/rungN-fresh-clone-N/...` paths rewritten to
  `<validator_cwd>/...`.
- All `/tmp/rungN-fresh-clone-N/...` paths rewritten to
  `<validator_cwd>/...`.
- `/tmp/empty-diff` rewritten to `<validator_cwd>`.

The suffix on each path is preserved (so a reviewer can still
see `api/llms_txt.py`, `README.md`, etc.). An absolute machine-
local path becomes a relative-like, machine-neutral token.

This is the only sanitization done. No other fields are
modified; envelopes inside their content are verbatim copies.

## Reproduction commands

Copy-paste block — each line `python3 ...` is one expected
verdict line printed by the gate.

### Live (rung 3 LIVE) — expect GREEN across all three gates

```
cd /path/to/clone/adversarial-sprint-dev-factory-build-gate-tools

# rung 3 LIVE
python3 tools/fixtures/rung3-gate.py --exit-loud \
  --envelope    tools/fixtures/evidence/rung3-envelope.json \
  --session-jsonl tools/fixtures/evidence/rung3-session.jsonl
# expected: GREEN — rung 3 gate: real run + tool calls + tokens present.
#           num_turns=2, tool_calls_total=2, tokens input/output = 13612/1661,
#           tool names used = ['Read']

# rung 5 LIVE
python3 tools/fixtures/rung5-gate.py --exit-loud \
  --envelope    tools/fixtures/evidence/rung3-envelope.json \
  --session-jsonl tools/fixtures/evidence/rung3-session.jsonl
# expected: GREEN — rung 5 gate. Tool calls present and clean; required source file inspected.
#           tool_use[1] name='Read' file='<validator_cwd>/README.md'
#           tool_use[2] name='Read' file='<validator_cwd>/api/llms_txt.py'

# rung 6 LIVE
python3 tools/fixtures/rung6-gate.py --exit-loud \
  --envelope    tools/fixtures/evidence/rung3-envelope.json \
  --session-jsonl tools/fixtures/evidence/rung3-session.jsonl
# expected: GREEN — rung 6 gate: decision 'REJECT' + doubled-charset finding present.
```

### Config A (rung 7 — empty diff + default tools; validator reads source + fabricates REJECT)

```
# rung 3
python3 tools/fixtures/rung3-gate.py --exit-loud \
  --envelope    tools/fixtures/evidence/rung7A-envelope.json \
  --session-jsonl tools/fixtures/evidence/rung7A-session.jsonl
# expected: GREEN — num_turns=3, tool_calls_total=3, tokens=15465/3179, names=['Grep','Read']

# rung 5
python3 tools/fixtures/rung5-gate.py --exit-loud \
  --envelope    tools/fixtures/evidence/rung7A-envelope.json \
  --session-jsonl tools/fixtures/evidence/rung7A-session.jsonl
# expected: GREEN — all is_error=False; api/llms_txt.py read present

# rung 6
python3 tools/fixtures/rung6-gate.py --exit-loud \
  --envelope    tools/fixtures/evidence/rung7A-envelope.json \
  --session-jsonl tools/fixtures/evidence/rung7A-session.jsonl
# expected: RED — no recognized Verdict/Decision line in text
#          (model used "# REJECT" not "## Verdict: REJECT"; template mismatch)
```

This is the documented rung-7 Config A asymmetry: the gates
can't catch the validator's false-positive REJECT triggered by
Read of the source file when the diff under review is empty.
This is intentional — it's the "isolation leak" filed in
`tools/KNOWN-ISSUES.md` (rung-8+ work).

### Config B (rung 7 — empty diff + blocked tools; validator emits ACCEPT)

```
# rung 3
python3 tools/fixtures/rung3-gate.py --exit-loud \
  --envelope    tools/fixtures/evidence/rung7B-envelope.json \
  --session-jsonl tools/fixtures/evidence/rung7B-session.jsonl
# expected: RED — tool_calls_count=0 (must be >= 1 — silent-green guard)

# rung 5
python3 tools/fixtures/rung5-gate.py --exit-loud \
  --envelope    tools/fixtures/evidence/rung7B-envelope.json \
  --session-jsonl tools/fixtures/evidence/rung7B-session.jsonl
# expected: RED — no Required-command coverage: validator did NOT read / inspect api/llms_txt.py

# rung 6
python3 tools/fixtures/rung6-gate.py --exit-loud \
  --envelope    tools/fixtures/evidence/rung7B-envelope.json \
  --session-jsonl tools/fixtures/evidence/rung7B-session.jsonl
# expected: RED — no recognized Verdict/Decision line in text
#          ("# ACCEPT" not "## Verdict: ACCEPT-WITH-NITS or REJECT")
```

## Quick TL;DR for impatient reviewers

Three commands. From the repo root, copy-paste this:

```
python3 tools/fixtures/rung3-gate.py --exit-loud \
   --envelope tools/fixtures/evidence/rung3-envelope.json \
   --session-jsonl tools/fixtures/evidence/rung3-session.jsonl 2>&1 | grep GREEN
python3 tools/fixtures/rung5-gate.py --exit-loud \
   --envelope tools/fixtures/evidence/rung3-envelope.json \
   --session-jsonl tools/fixtures/evidence/rung3-session.jsonl 2>&1 | grep GREEN
python3 tools/fixtures/rung6-gate.py --exit-loud \
   --envelope tools/fixtures/evidence/rung3-envelope.json \
   --session-jsonl tools/fixtures/evidence/rung3-session.jsonl 2>&1 | grep GREEN
```

All three should print `GREEN`. If any prints `RED`, the seam
refactor is NOT behavior-preserving on this commit's evidence
— STOP and report.

## What this reproduction DOES NOT cover (out-of-scope)

- The rung-7 Config A false-positive REJECT — gates cannot catch
  it today (see `tools/KNOWN-ISSUES.md` Issue: "False-REJECT via
  source-read (isolation leak)"). A reviewer should see a RED on
  the rung-6 gate for Config A.
- The rung-7 Config B fail-loud verdict — the brief asks "fail
  loud"; rung-3/5/6 RED together **is** the fail-loud signal.
- Phase-4 vendor adapters (Codex, Anthropic, Ollama) — only
  Factory is implemented as the proof vendor.

## What's NOT in this bundle (commit-message honesty)

- `build-evidence/` from the audit-run machine — untracked by
  design; each raw envelope file (≈ 727 B / 564 B / 406 B) is
  re-encoded as the sanitized copy under `tools/fixtures/evidence/`.
- The executor's BUILD-LOG / its own transcript — explicitly NOT
  included; the validator must stay blind to executor reasoning.
  The committed evidence is what the validator saw, not what the
  executor saw.

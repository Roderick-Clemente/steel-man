# Fake pass

A forged transcript passed every gate with zero real validation. Three permissive defaults aligned: an unmatched `tool_use` returned `is_error=None`, the gate checked `is True`, and the run-level `is_error` flag was ignored. The fix is one line. The forged input is committed as a fixture so the failure can be reproduced.

## The three holes

`tools/KNOWN-ISSUES.md` records the exact mechanism under "Issue: Fake-pass via unmatched tool_use (is_error=None)."

1. `tools/adapters/factory.py` returns one dict per matched-or-unmatched `tool_use` event. When a `tool_use` has no matching `tool_result` in the same session JSONL, the dict reports `is_error=None`. The contract therefore permits "no evidence the tool actually ran" to pass as "no evidence it errored."

2. `tools/fixtures/rung5-gate.py` failed only when `tc.get("is_error") is True`. `None` slipped through. The gate had no proof the tool ran, but also no proof it errored, so it counted the call as clean.

3. `tools/adapters/factory.py` captured the run-level `is_error` flag into the normalized envelope, but rungs 3, 5, and 6 did not read it. An aborted or errored run could green if the tools and prose looked right.

Together, these three defaults let a fabricated transcript mint a green ladder.

## The committed fixture

`tools/fixtures/rung7b-fakepass/` contains the forged input:

- `fake-envelope.json` reports `num_turns: 2`, `is_error: false`, non-zero tokens, and a fully formed `## Verdict: REJECT` with a doubled-charset finding.
- `fake-session.jsonl` contains one assistant message with a single `tool_use` event named `Read` against `api/llms_txt.py`. There is no matching `tool_result`. The validator never actually ran the tool.

Pre-fix, the gates behaved like this:

- rung 3 was green because `tool_calls_total=1` and the tool name was in the allowlist.
- rung 5 was green because no `is_error is True` violation existed and the lone `Read` satisfied the required-source coverage.
- rung 6 was green because the `## Verdict: REJECT` and `charset=utf-8; charset=utf-8` strings matched the expected regexes.

Zero real validation. Full green ladder. `tools/fixtures/rung7-reflection.md` documents the rung-7 negative-control work that isolated the same class of failure from a live validator rather than a hand-forged input.

## The fix

Two changes close the hole:

1. In `tools/fixtures/rung5-gate.py`, the failure condition becomes `if tc.get("is_error") is not False`. A tool call that is not provably clean is not clean. This one line covers both `True` and `None`.

2. After normalizing, every gate must thread-check `envelope.is_error`. If the run-level error flag is `True`, the gate fails regardless of tools or prose.

The fixture was verified by Codex and Grok validators in blind measurement runs, and by hand reproduction. After the fix, the rung7b fixture exits non-zero on all three gates. The live matrix remained unbroken. The fixture is now a permanent regression test: any change that reintroduces the old `is True` check will fail against the committed input.

`tools/fixtures/rung7-reflection.md` is the companion record that isolates the same class from a live validator rather than a hand-forged input. It ran two configurations against an empty diff: one with default tools, where the validator fabricated a doubled-charset finding from source; and one with `Read` and `Grep` stripped, where all three gates failed loud. The fake-pass fixture and the rung-7 reflection together cover both halves of the problem: a synthetic transcript that looks green, and a live validator that over-claims when given too much source access.

## Why this is the project's failure mode

The fake-pass is the silent-green finding in its purest form: the artifacts look right, the transcript exists, the verdict is well-formed, and none of it is connected to a real tool execution. The framework exists to catch exactly this shape. A gate that checks whether something looks green is not enough; it must check whether the green is grounded in evidence. See [silent green](silent-green.md) for the broader platform failure mode, [reference guard](reference-guard.md) for the guard that closes the related isolation hole, and [the method](../method.md) for the invariant that validation must be blocking and evidence-based.

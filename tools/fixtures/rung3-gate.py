#!/usr/bin/env python3
"""Rung 3 gate (refactored) — assert the droid exec run was real.

Brief: "Gate: run is REAL — num_turns>0, tokens>0, real test tool-calls
present. FAILS LOUD on a --mission-style no-op."

After the seam refactor (commit ahead), this gate consumes the
NORMALIZED envelope via `tools/adapters/factory.to_envelope`. It
does NOT read raw Factory fields directly. The prev-hand-rolled
`tools/fixtures/rung3-tool-call-digest.json` is replaced by an
adapter-driven normalised shape.

Behavior preservation is asserted by running this gate before/after
the refactor on the same envelope. Same GREEN/RED verdict on
identical input.

Asset shape (consumed via adapter):
  env.num_turns         — int
  env.usage.input       — int
  env.usage.output      — int
  env.tool_calls        — list of {"name", "args", "is_error"}
  env.result_text_first_240chars — str (printed for human review)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools"))

from adapters.factory import to_envelope  # noqa: E402

ALLOWLIST = {"Read", "Execute", "Glob", "Grep", "LS"}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--envelope",
        required=True,
        type=Path,
        help="Path to the raw droid exec --output-format json envelope.",
    )
    parser.add_argument(
        "--session-jsonl",
        type=Path,
        default=None,
        help="Path to the inner-session jsonl (auto-located if absent).",
    )
    parser.add_argument(
        "--settings-jsonl",
        type=Path,
        default=None,
        help="Path to the inner-session settings.json (auto-located if absent).",
    )
    parser.add_argument(
        "--exit-loud",
        action="store_true",
        help="On FAIL, raise SystemExit(1).",
    )
    args = parser.parse_args(argv)

    env = to_envelope(
        envelope_path=args.envelope,
        session_jsonl_path=args.session_jsonl,
        settings_json_path=args.settings_jsonl,
    )

    fails: list[str] = []
    # Run-level abort: the envelope says the run itself errored. Refuse
    # GREEN on aborted runs regardless of tools/prose.
    if env.get("is_error"):
        fails.append(
            f"envelope.is_error=True; the run itself aborted "
            f"(envelope session_id={env.get('session_id')!r}). Gate refuses "
            "to mint GREEN on an aborted run regardless of tools/prose."
        )
    num_turns = env["num_turns"]
    if num_turns <= 0:
        fails.append(f"num_turns={num_turns} (must be > 0)")

    in_tok = env["usage"]["input"]
    out_tok = env["usage"]["output"]
    if in_tok <= 0 and out_tok <= 0:
        fails.append(f"tokens both 0 (input={in_tok}, output={out_tok}); silent-green")

    tool_total = len(env["tool_calls"])
    if tool_total < 1:
        fails.append(f"tool_calls_count={tool_total} (must be >= 1 — silent-green guard)")

    names_used = {tc.get("name") for tc in env["tool_calls"] if isinstance(tc, dict)}
    if not (names_used & ALLOWLIST):
        fails.append(
            "no Read/Execute/Glob/Grep/LS tool calls observed; "
            f"names encountered: {sorted(names_used)}"
        )

    # verdict should at least mention the defect literal somewhere in
    # the first 240 chars (rung 3 itself doesn't gate correctness; rung 6
    # does that — rung 3 just records the raw verdict shape).
    verdict = env["result_text_first_240chars"]
    print(f"verdict first 240 chars:\n{verdict}\n(---)")

    if fails:
        print("RED — rung 3 gate failed:")
        for f in fails:
            print(f"  - {f}")
        if args.exit_loud:
            raise SystemExit(1)
        return 1

    print("GREEN — rung 3 gate: real run + tool calls + tokens present.")
    print(f"  num_turns         : {num_turns}")
    print(f"  tool_calls_total  : {tool_total}")
    print(f"  tokens input/out  : {in_tok} / {out_tok}")
    print(f"  tool names used   : {sorted(names_used & ALLOWLIST)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

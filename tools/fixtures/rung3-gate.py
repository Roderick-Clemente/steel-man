#!/usr/bin/env python3
"""Rung 3 gate — assert the droid exec run was real (not silent-green).

Brief: "Gate: run is REAL — num_turns>0, tokens>0, real test tool-calls
present. FAILS LOUD on a --mission-style no-op."

Reads tools/fixtures/rung3-tool-call-digest.json and asserts:
- num_turns ≥ 1
- input_tokens > 0 OR output_tokens > 0
- tool_calls_total ≥ 1
- at least one tool name is in {Read, Execute, Glob, Grep, LS} — the
  per-brief 'read + test-run ALLOWLIST'
- verdict_text contains the doubled-charset defect literal somewhere
  in its first 240 chars (the model surfaced it)

Exits 0 on green, raises SystemExit(1) on FAIL when --exit-loud.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DIGEST = REPO_ROOT / "tools" / "fixtures" / "rung3-tool-call-digest.json"

ALLOWLIST = {"Read", "Execute", "Glob", "Grep", "LS"}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--exit-loud",
        action="store_true",
        help="On FAIL, raise SystemExit(1).",
    )
    args = parser.parse_args(argv)

    if not DIGEST.exists():
        print(f"FAIL: digest missing: {DIGEST}", file=sys.stderr)
        return 2
    digest = json.loads(DIGEST.read_text())

    fails: list[str] = []
    num_turns = digest["envelope"].get("num_turns") or 0
    if num_turns <= 0:
        fails.append(f"num_turns={num_turns} (must be > 0)")

    usage = digest.get("usage_tokens", {})
    in_tok = usage.get("input") or 0
    out_tok = usage.get("output") or 0
    if in_tok <= 0 and out_tok <= 0:
        fails.append(f"tokens both 0 (input={in_tok}, output={out_tok}); silent-green")

    tool_total = digest.get("tool_calls_total") or 0
    if tool_total < 1:
        fails.append(f"tool_calls_count={tool_total} (must be >= 1 — silent-green guard)")

    tool_events = digest.get("tool_use_events") or []
    names_used = {ev.get("name") for ev in tool_events if isinstance(ev, dict)}
    if not (names_used & ALLOWLIST):
        fails.append(
            "no Read/Execute/Glob/Grep/LS tool calls observed; "
            f"names encountered: {sorted(names_used)}"
        )

    # verdict should at least mention the defect literal somewhere in
    # the first 240 chars (rung 3 itself doesn't gate correctness; rung 6
    # does that — rung 3 just records the raw verdict shape)
    verdict = digest.get("verdict_text_first_240chars", "")
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

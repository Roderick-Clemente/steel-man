#!/usr/bin/env python3
"""Rung 2 — canary: assert no executor transcript leaks into the blind prompt.

The brief: "a canary asserts BUILD-LOG.md / any executor transcript is
ABSENT from the rendered prompt FILE (assert file contents, not intent)."

This script reads tools/fixtures/blind-prompt.txt and asserts it is free
of any transcript markers. Exit 0 on PASS (prompt is clean of transcripts),
exit non-zero on FAIL (transcript markers leaked).

Forbidden markers (chosen from this session's history + canonical CLI shape):
- BUILD-LOG.md (literal file name, present in earlier evidence artifacts)
- /llms.txt-handler-pilot/BUILD-LOG.md
- hook-attempts.jsonl (private hook instrumentation log)
- a4-bypass-reproduction.md
- factory-credits-none.md
- model-availability.md (executor's per-model availability notes)
- "Final answer:" (generic transcript shape from droid exec)
- "is_error=" (generic transcript shape from tool-call summaries)
- "num_turns=" (generic envelope shape)
- "tool_use_id=" (Anthropic-style transcript marker)
- telemetry, factory_credits, raw_hive_payload
- raw transcript-like JSON: "stop_reason", "usage:", "type":"message"

NOTE: the diff section IS allowed to mention these if the diff itself
happens to reference them — that's the universe of the validator. The
canary is concerned about LEAKED transcripts, not about the spec
referencing itself. We do a coarse substring count; if any forbidden
substring appears in the prompt, the canary raises. Hitting canary is a
bug at this rung.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PROMPT_PATH = REPO_ROOT / "tools" / "fixtures" / "blind-prompt.txt"

FORBIDDEN = (
    # evidence-artifact file names (literal)
    "BUILD-LOG.md",
    "/llms.txt-handler-pilot/BUILD-LOG.md",
    "hook-attempts.jsonl",
    "a4-bypass-reproduction.md",
    "factory-credits-none.md",
    "model-availability.md",
    "tools/pilot-llms-txt-spec.md",  # spec is referenced via spec_path content, not literal file name
    # generic transcript shapes
    "Final answer:",
    "is_error=",
    "num_turns=",
    "tool_use_id=",
    "stop_reason",
    "factory_credits",
    "hive_payload",
)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--exit-loud",
        action="store_true",
        help="On FAIL, raise SystemExit(1) to fail loud per brief's silent-green rule.",
    )
    args = parser.parse_args(argv)

    if not PROMPT_PATH.exists():
        print(f"rung 2 canary: prompt missing: {PROMPT_PATH}", file=sys.stderr)
        return 2

    text = PROMPT_PATH.read_text()
    leaks: list[tuple[str, int]] = []
    for needle in FORBIDDEN:
        i = 0
        while True:
            pos = text.find(needle, i)
            if pos == -1:
                break
            leaks.append((needle, pos))
            i = pos + 1

    if leaks:
        print(f"rung 2 canary FAIL: {len(leaks)} transcript leak(s):", file=sys.stderr)
        for needle, pos in leaks:
            line = text.count("\n", 0, pos) + 1
            print(f"  - {needle!r} at byte {pos} (line ~{line})", file=sys.stderr)
        if args.exit_loud:
            raise SystemExit(1)
        return 1

    print(f"rung 2 canary: prompt is clean of transcript markers ({len(text)} bytes).")
    print(f"  forbidden markers checked: {len(FORBIDDEN)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

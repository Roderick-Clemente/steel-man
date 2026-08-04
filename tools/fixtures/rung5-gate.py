#!/usr/bin/env python3
"""Rung 5 gate (refactored) — gate ONLY on machine-verifiable tool-call events.

Brief: "parse the JSON verdict, but gate ONLY on machine-verifiable
tool-call events (is_error=false + exit codes + required-command
coverage), NEVER transcript prose."

After the seam refactor (commit ahead), this gate consumes the
NORMALIZED envelope's `tool_calls` field via
`tools/adapters/factory.to_envelope`. It does NOT parse Factory
inner-session jsonl directly. The required-source-coverage path
criterion (`api/llms_txt.py`) is unchanged; only where the events
come from is moved behind the adapter.

Behavior preservation is asserted by running this gate before/after
the refactor on the same envelope. Same GREEN/RED verdict on
identical input.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools"))

from adapters.factory import to_envelope  # noqa: E402


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--envelope",
        required=True,
        type=Path,
        help="Path to the raw droid exec envelope.",
    )
    parser.add_argument(
        "--session-jsonl",
        type=Path,
        default=None,
        help="Path to the inner-session jsonl (auto-located if absent).",
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
    )
    tool_calls = env["tool_calls"]
    file_paths = [
        (tc.get("args") or {}).get("file_path") or (tc.get("args") or {}).get("path")
        for tc in tool_calls
    ]
    file_paths = [fp for fp in file_paths if isinstance(fp, str)]

    print(f"tool_use   : {len(tool_calls)}")
    for i, tc in enumerate(tool_calls, 1):
        fp = (tc.get("args") or {}).get("file_path")
        cmd = (tc.get("args") or {}).get("command")
        print(
            f"  tool_use[{i}] name={tc.get('name')!r}  file={fp!r}  cmd={cmd!r}  is_error={tc.get('is_error')!r}"
        )

    fails: list[str] = []
    saw_llms_txt_source_inspection = any(
        fp and fp.endswith("api/llms_txt.py") for fp in file_paths
    )
    if not saw_llms_txt_source_inspection:
        fails.append(
            "no Required-command coverage: validator did NOT read / inspect api/llms_txt.py. "
            f"file_paths seen: {file_paths}"
        )
    for tc in tool_calls:
        if tc.get("is_error") is True:
            fails.append(
                f"tool_call marked is_error=True: name={tc.get('name')!r} args={tc.get('args')!r}"
            )

    if fails:
        print()
        print("RED — rung 5 gate failed:")
        for f in fails:
            print(f"  - {f}")
        if args.exit_loud:
            raise SystemExit(1)
        return 1

    print()
    print("GREEN — rung 5 gate. Tool calls present and clean; required source file inspected.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

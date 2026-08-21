#!/usr/bin/env python3
"""Rung 2 — render a blind validator prompt.

Output writes tools/fixtures/blind-prompt.txt which is spec + diff ONLY.
This prompt is what we'll feed to a non-Claude model via droid exec at
rung 3. The blunt rule: no executor transcript may leak into the prompt
(this is the whole point of the blind prompt — keep the model honest by
giving it only the spec and the diff).

Usage:
    python3 tools/render-blind-prompt.py
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PIN_PATH = REPO_ROOT / "tools" / "fixtures" / "doubled-charset-pin.json"
SPEC_PATH = REPO_ROOT / "tools" / "validator-spec" / "llms-doubled-charset.md"
OUT_PATH = REPO_ROOT / "tools" / "fixtures" / "blind-prompt.txt"


def _git_diff(source_clone: str, base: str, head: str, paths: list[str]) -> str:
    out = subprocess.run(
        ["git", "diff", f"{base}..{head}", "--", *paths],
        cwd=source_clone,
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=str(OUT_PATH),
        help="Output path for the rendered prompt. Defaults to tools/fixtures/blind-prompt.txt.",
    )
    args = parser.parse_args(argv)

    if not PIN_PATH.exists():
        print(f"FAIL: rung-1 pin missing: {PIN_PATH}", file=sys.stderr)
        return 2
    if not SPEC_PATH.exists():
        print(f"FAIL: spec missing: {SPEC_PATH}", file=sys.stderr)
        return 2

    pin = json.loads(PIN_PATH.read_text())
    base = pin["fixture"]["base_sha"]
    head = pin["fixture"]["head_sha"]
    diff_paths = pin["fixture"]["diff_paths"]
    source_clone = pin["fixture"]["source_local_clone"]

    spec_text = SPEC_PATH.read_text()
    diff_text = _git_diff(source_clone, base, head, diff_paths)

    rendered = (
        f"{spec_text}"
        "\n\n"
        "============================================================\n"
        "DIFF (verbatim, unified format)\n"
        f"base = {base}\n"
        f"head = {head}\n"
        f"paths = {diff_paths}\n"
        f"diff_sha256 = {pin['fixture']['diff_sha256']}\n"
        "============================================================\n"
        "\n"
        f"{diff_text}"
    )

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(rendered)
    print(f"wrote {args.out}")
    print(f"  size: {len(rendered)} bytes")
    print(f"  spec bytes: {len(spec_text)}")
    print(f"  diff bytes: {len(diff_text)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

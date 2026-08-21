#!/usr/bin/env python3
"""Rung 3 envelope extractor (refactored) — thin wrapper over the Factory adapter.

Brief: "extract the inner-session tool_use events" — historically
this script hardcoded the `~/.factory/sessions/-private-tmp-…`
path search and the droid-exec envelope field names.

After the seam refactor (commit ahead), this script delegates to
`tools/adapters/factory.to_envelope`, which owns those
vendor-specifics. The script remains as a CLI utility that
emits a digest-shape file expected by downstream tooling
(`tools/fixtures/rung3-tool-call-digest.json`).

Behavior preservation is asserted by running this script
before/after the refactor on the same envelope and comparing
outputs.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools"))

from adapters.factory import locate_sibling_files, to_digest_shape, to_envelope  # noqa: E402


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
        "--out",
        type=Path,
        required=True,
        help="Path to the digest-shape output JSON.",
    )
    args = parser.parse_args(argv)

    if args.session_jsonl is None or args.settings_jsonl is None:
        siblings = locate_sibling_files(args.envelope)
        if args.session_jsonl is None:
            args.session_jsonl = siblings["session_jsonl"]
        if args.settings_jsonl is None:
            args.settings_jsonl = siblings["settings_json"]

    env = to_envelope(
        envelope_path=args.envelope,
        session_jsonl_path=args.session_jsonl,
        settings_json_path=args.settings_jsonl,
    )
    digest = to_digest_shape(env)
    args.out.write_text(json.dumps(digest, indent=2))
    print(f"wrote {args.out} (digest of session {env['session_id']!r})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

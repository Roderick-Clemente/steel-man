#!/usr/bin/env python3
"""Token accounting for the §3.2 fairness rule (SPIKE §3.2).

The fairness rule: the win is real ONLY IF
    tokens(evidence bundle read) < tokens(in-session raw test output it replaces)

This module measures both sides:
  - **Control arm** (`evidence_source=in-session`): the validator ran pytest and
    ingested raw stdout. `raw_test_output_tokens` = token count of that stdout.
  - **Treatment arm** (`evidence_source=bundle`): the validator read the bundle.
    `mcp_payload_tokens` = token count of the bundle JSON that entered context.

Token estimation: chars / 4 (the standard approximation for English/JSON text).
This is a proxy; the real experiment would use the provider's tokenizer, but the
proxy is sufficient to demonstrate the mechanism and get directional numbers.

Usage:
    python3 phase-3.2/evidence/token_accounting.py \
        --raw-output phase-3.2/build-evidence/chunk1-raw-pytest.txt \
        --bundle phase-3.2/build-evidence/chunk1-bundle.json \
        --output phase-3.2/build-evidence/chunk1-token-accounting.json
"""
import argparse
import json
import os
import sys


def estimate_tokens(text: str) -> int:
    """Estimate token count as len(text) // 4 (standard proxy)."""
    return len(text) // 4


def file_token_count(path: str) -> int:
    with open(path) as f:
        return estimate_tokens(f.read())


def main() -> int:
    parser = argparse.ArgumentParser(description="Token accounting for §3.2 fairness rule.")
    parser.add_argument("--raw-output", required=True,
                        help="Path to the raw pytest output (the in-session cost being replaced).")
    parser.add_argument("--bundle", required=True,
                        help="Path to the EvidenceBundle JSON (the replacement cost).")
    parser.add_argument("--output", required=True,
                        help="Path to write the token accounting JSON.")
    args = parser.parse_args()

    raw_tokens = file_token_count(args.raw_output)
    bundle_tokens = file_token_count(args.bundle)

    saving = raw_tokens - bundle_tokens
    saving_pct = (saving / raw_tokens * 100) if raw_tokens > 0 else 0

    result = {
        "control_raw_test_output_tokens": raw_tokens,
        "treatment_bundle_read_tokens": bundle_tokens,
        "saving_tokens": saving,
        "saving_pct": round(saving_pct, 1),
        "fairness_rule_holds": bundle_tokens < raw_tokens,
        "note": (
            "Token estimate = chars // 4 (proxy). "
            "The fairness rule (SPIKE §3.2) holds iff treatment < control. "
            "This measures ONLY the test-output-read slice (2) of the validator run; "
            "diff-read (1) and verdict-reasoning (3) do not move."
        ),
    }

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(result, f, indent=2)

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Compute and record a SHA-256 lock manifest for an accepted test file.

Usage:
    python3 phase-1/scripts/lock.py <test-file> <accepted-assertion>
        [--pilot-root <path>] [--locks-dir <path>]

The manifest is written to phase-1/locks/<test-file>.lock.json, preserving
any directory separators in the test-file path so a single lock directory
can hold tests from different pilot-repo subdirectories.
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone


def compute_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Lock a test file by content hash.")
    parser.add_argument("test_file", help="Path to the test file, relative to the pilot repo.")
    parser.add_argument(
        "accepted_assertion",
        help="The intended assertion that must fail for a valid RED.",
    )
    parser.add_argument(
        "--pilot-root",
        default=os.getcwd(),
        help="Absolute or relative path to the pilot repo root (default: cwd).",
    )
    parser.add_argument(
        "--locks-dir",
        default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "locks"),
        help="Directory where lock manifests are written.",
    )
    args = parser.parse_args()

    pilot_root = os.path.abspath(args.pilot_root)
    abs_test_path = os.path.join(pilot_root, args.test_file)

    if not os.path.isfile(abs_test_path):
        print(f"ERROR: test file not found: {abs_test_path}", file=sys.stderr)
        return 1

    sha = compute_sha256(abs_test_path)
    accepted_at = datetime.now(timezone.utc).isoformat()

    manifest = {
        "file": args.test_file,
        "sha256": sha,
        "accepted_at": accepted_at,
        "accepted_assertion": args.accepted_assertion,
    }

    # Preserve subdirectory structure under the locks directory so that
    # test/test_foo.py becomes locks/test/test_foo.py.lock.json.
    lock_path = os.path.join(args.locks_dir, f"{args.test_file}.lock.json")
    os.makedirs(os.path.dirname(lock_path), exist_ok=True)

    with open(lock_path, "w") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")

    print(f"LOCKED {args.test_file}")
    print(f"sha256: {sha}")
    print(f"manifest: {lock_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

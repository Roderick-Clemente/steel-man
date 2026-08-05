#!/usr/bin/env python3
"""Green verification gate for a locked test.

Recomputes the locked test file's SHA-256 and runs the test. Refuses GREEN
unless the hash matches the manifest AND the test passes for the intended
assertion.

Usage:
    python3 phase-1/scripts/verify-green.py --pilot-root <path> \
        --lock-file <path> --test-file <path>
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys


def compute_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def run_pytest(pilot_root: str, test_file: str):
    cmd = [sys.executable, "-m", "pytest", test_file, "-v"]
    return subprocess.run(
        cmd,
        cwd=pilot_root,
        capture_output=True,
        text=True,
        timeout=120,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify GREEN on a locked test.")
    parser.add_argument("--pilot-root", required=True, help="Path to the pilot repo root.")
    parser.add_argument("--lock-file", required=True, help="Path to the lock manifest JSON.")
    parser.add_argument("--test-file", required=True, help="Test file path relative to pilot root.")
    args = parser.parse_args()

    with open(args.lock_file) as f:
        manifest = json.load(f)

    expected_sha = manifest.get("sha256")
    accepted_assertion = manifest.get("accepted_assertion", "")

    abs_test_path = os.path.join(os.path.abspath(args.pilot_root), args.test_file)
    if not os.path.isfile(abs_test_path):
        print(f"GREEN REFUSED: test file missing: {abs_test_path}", file=sys.stderr)
        return 1

    current_sha = compute_sha256(abs_test_path)
    if current_sha != expected_sha:
        print("GREEN REFUSED: locked test content changed", file=sys.stderr)
        print(f"  expected: {expected_sha}", file=sys.stderr)
        print(f"  actual:   {current_sha}", file=sys.stderr)
        return 1

    result = run_pytest(args.pilot_root, args.test_file)
    if result.returncode != 0:
        print("GREEN REFUSED: test does not pass after implementation", file=sys.stderr)
        print("--- stdout ---", file=sys.stderr)
        print(result.stdout, file=sys.stderr)
        print("--- stderr ---", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        return 1

    # Re-run the assertion check so the reported reason matches the locked
    # assertion phrase, even if pytest passed with a different success shape.
    combined = f"{result.stdout}\n{result.stderr}"
    if accepted_assertion and accepted_assertion.lower() not in combined.lower():
        print(
            "GREEN REFUSED: test passed but the accepted assertion phrase is not visible in output",
            file=sys.stderr,
        )
        return 1

    print("GREEN ACCEPTED")
    print(f"  test_file: {args.test_file}")
    print(f"  sha256:    {current_sha}")
    print(f"  pytest:    exit 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())

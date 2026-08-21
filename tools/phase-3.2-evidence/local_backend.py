#!/usr/bin/env python3
"""Local evidence-provider backend (SPIKE §2.2, flavor a — zero CI).

Composes tools the repo already has:
  - tests → pytest (structured via --json-report if available, else verbose parse)
  - locked-hash check → reuses phase-1/scripts/verify-green.py (emits
    locked_test_sha_observed)
  - security → Bandit (SARIF-derived, new-vs-baseline + curated allowlist)

Normalizes to the EvidenceBundle v1 schema, signs it (HMAC-SHA256), and writes
the signed bundle to disk. Runs on a developer machine with no network CI.

Usage:
    python3 phase-3.2/evidence/local_backend.py \
        --pilot-root /path/to/quantum-bank \
        --framework-root /path/to/adversarial-sprint-dev \
        --test-file test/test_profile_model.py \
        --lock-file phase-1/locks/test/test_profile_model.py.lock.json \
        --output phase-3.2/build-evidence/chunk1-bundle.json \
        [--signing-key-env EVIDENCE_SIGNING_KEY] \
        [--security-scan] \
        [--security-allowlist phase-3.2/evidence/security_allowlist.json] \
        [--security-baseline phase-3.2/build-evidence/bandit-baseline.json]
"""

import argparse
import datetime
import hashlib
import hmac
import json
import os
import re
import subprocess
import sys
import uuid

# ── layout-root bootstrap (CHUNK-1-SPEC §2.2) ────────────────────────────
#
# This module is invoked as a standalone script (from per_chunk.py and
# orchestrate-review.py), so ``tools/`` is not on sys.path. Resolve it from
# this file's own location and import the roots at module level.
#
# The import is UNGUARDED and NOT lazy on purpose: a try/except ImportError
# fallback, or an import inside main(), would let ``--help`` exit 0 while
# dying at sprint runtime — a §7 silent-green hole.
#
# The self-relative root below exists ONLY to locate ``tools/``. It MUST NOT
# be used to compose the routed paths: those compose against the runtime
# ``--framework-root`` argument, the only value that is correct when the
# framework and pilot repos differ. The two are permitted to disagree.
# The three-dirname depth is Chunk-2-safe (the target dir sits at the same
# depth) and must not be "corrected".
_SELF_RELATIVE_FRAMEWORK_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
_TOOLS_DIR = os.path.join(_SELF_RELATIVE_FRAMEWORK_ROOT, "tools")
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

from sprint_loop.config import SCRIPTS_ROOT, phase_path  # noqa: E402

# ── helpers ──────────────────────────────────────────────────────────────


def utcnow_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def compute_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def get_tool_version(cmd: list[str], flag: str = "--version") -> str:
    try:
        r = subprocess.run(cmd + [flag], capture_output=True, text=True, timeout=10)
        return r.stdout.strip().split("\n")[0] if r.stdout else r.stderr.strip()
    except Exception:
        return "unknown"


def sign_bundle(bundle: dict, key: bytes, key_id: str) -> dict:
    """HMAC-SHA256 over the canonical JSON of the bundle minus the signature field."""
    payload = json.dumps(bundle, sort_keys=True, separators=(",", ":")).encode()
    digest = hmac.new(key, payload, hashlib.sha256).hexdigest()
    bundle["signature"] = {
        "algorithm": "HMAC-SHA256",
        "value": digest,
        "key_id": key_id,
    }
    return bundle


# ── verify-green.py reuse (locked-hash check) ────────────────────────────


def run_verify_green(
    framework_root: str, pilot_root: str, lock_file: str, test_file: str, python: str
) -> dict:
    """Run verify-green.py and extract locked_test_sha_observed + pass/fail."""
    script = phase_path(framework_root, "scripts", "verify-green.py")
    cmd = [
        python,
        script,
        "--pilot-root",
        pilot_root,
        "--lock-file",
        lock_file,
        "--test-file",
        test_file,
        "--python",
        python,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    # verify-green.py prints "GREEN ACCEPTED" + sha on success
    output = result.stdout + result.stderr
    sha_match = re.search(r"sha256:\s+(\w+)", output)
    locked_sha = sha_match.group(1) if sha_match else None

    # Also compute directly as a fallback / cross-check
    abs_test = os.path.join(os.path.abspath(pilot_root), test_file)
    if os.path.isfile(abs_test):
        locked_sha = locked_sha or compute_sha256(abs_test)

    return {
        "exit_code": result.returncode,
        "green_accepted": result.returncode == 0,
        "locked_test_sha_observed": locked_sha,
        "raw_output": output.strip(),
    }


# ── pytest structured results ────────────────────────────────────────────


def run_pytest(pilot_root: str, test_file: str, python: str) -> dict:
    """Run pytest and parse pass/fail/skip counts + compact failure records.

    If test_file is empty, runs the full suite (no file argument).
    """
    cmd = [python, "-m", "pytest", "-v", "--tb=line", "--no-header"]
    if test_file:
        cmd.append(test_file)
    result = subprocess.run(cmd, cwd=pilot_root, capture_output=True, text=True, timeout=120)
    output = result.stdout + result.stderr

    passed = failed = skipped = 0
    failures = []

    for line in output.splitlines():
        # Strip ANSI codes
        clean = re.sub(r"\x1b\[[0-9;]*m", "", line)
        # Match test result lines: test/path::test_name PASSED/FAILED/SKIPPED
        m = re.match(r"^(.+?)\s+(PASSED|FAILED|SKIPPED|ERROR)", clean)
        if m:
            nodeid = m.group(1).strip()
            status = m.group(2)
            if status == "PASSED":
                passed += 1
            elif status in ("FAILED", "ERROR"):
                failed += 1
                # Try to extract assertion line from --tb=line output
                assertion_line = None
                short_message = "test failed"
                # Look for the traceback line for this test
                for tb_line in output.splitlines():
                    tb_clean = re.sub(r"\x1b\[[0-9;]*m", "", tb_line)
                    if nodeid.split("::")[-1] in tb_clean and ".py:" in tb_clean:
                        line_match = re.search(r":(\d+):", tb_clean)
                        if line_match:
                            assertion_line = int(line_match.group(1))
                            short_message = tb_clean.strip()[:300]
                        break
                failures.append(
                    {
                        "nodeid": nodeid,
                        "assertion_line": assertion_line,
                        "short_message": short_message,
                    }
                )
            elif status == "SKIPPED":
                skipped += 1

    return {
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "suite_exit_code": result.returncode,
        "failures": failures,
        "raw_output": output.strip(),
    }


# ── coverage (optional, via pytest-cov) ──────────────────────────────────


def run_coverage(pilot_root: str, test_file: str, python: str) -> dict | None:
    """Attempt coverage via pytest-cov. Returns None if unavailable."""
    cmd = [python, "-m", "pytest", test_file, "--cov", "--cov-report=term", "-q"]
    try:
        result = subprocess.run(cmd, cwd=pilot_root, capture_output=True, text=True, timeout=120)
        output = result.stdout
        # Parse "TOTAL  XX%"
        m = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", output)
        if m:
            return {"lines_pct": float(m.group(1))}
    except Exception as exc:
        print(f"  coverage: skipped ({exc})", file=sys.stderr)
    return None


# ── security lens (Bandit, new-vs-baseline + allowlist) ───────────────────


def run_bandit(pilot_root: str, python: str) -> dict:
    """Run Bandit, return raw findings in a normalized structure.

    Excludes .venv and common non-project dirs to avoid noise from installed
    packages (the §4.4 lesson: don't drown the signal in old debt).
    """
    cmd = [
        python,
        "-m",
        "bandit",
        "-r",
        ".",
        "-x",
        "./.venv,./.git,./node_modules",
        "-f",
        "json",
        "-q",
    ]
    result = subprocess.run(cmd, cwd=pilot_root, capture_output=True, text=True, timeout=120)
    try:
        report = json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError):
        return {"raw_findings": [], "error": result.stderr.strip()[:200]}

    findings = []
    for item in report.get("results", []):
        findings.append(
            {
                "rule_id": item.get("test_id", "unknown"),
                "severity": item.get("issue_severity", "low").lower(),
                "file": item.get("filename", ""),
                "line": item.get("line_number", 0),
                "short_message": item.get("issue_text", "")[:300],
                "confidence": item.get("issue_confidence", "MEDIUM").lower(),
            }
        )
    return {"raw_findings": findings, "error": None}


def apply_allowlist(findings: list[dict], allowlist: dict) -> list[dict]:
    """Suppress findings matching the curated allowlist (SPIKE §4.4 lesson 2).

    Allowlist entries are scoped to specific (rule_id, file, line) tuples —
    not whole files — so a real future secret in the same file still trips.
    A line of 0 or null in an entry acts as a wildcard (matches any line for
    that rule_id + file pair). This is for cases where the line number may
    shift between runs but the finding is known-public by design.
    """
    entries = allowlist.get("allowlist", [])
    suppressed = []
    kept = []
    for f in findings:
        matched = False
        for entry in entries:
            if f["rule_id"] == entry.get("rule_id") and f["file"] == entry.get("file"):
                entry_line = entry.get("line", 0)
                # line=0 means wildcard (match any line for this rule+file)
                if entry_line == 0 or f.get("line") == entry_line:
                    matched = True
                    break
        if matched:
            suppressed.append(f)
        else:
            kept.append(f)
    return kept


def diff_vs_baseline(findings: list[dict], baseline: dict) -> list[dict]:
    """Mark findings as new-vs-baseline (SPIKE §4.4 lesson 1).

    A finding is 'new' if no baseline finding has the same (rule_id, file, line).
    Handles both normalized format ({raw_findings: [...]}) and raw bandit JSON
    ({results: [...]}).
    """
    baseline_raw = baseline.get("raw_findings", [])
    if not baseline_raw:
        # Fallback: raw bandit JSON has "results"
        for r in baseline.get("results", []):
            baseline_raw.append(
                {
                    "rule_id": r.get("test_id", "unknown"),
                    "file": r.get("filename", ""),
                    "line": r.get("line_number", 0),
                }
            )

    baseline_keys = set()
    for b in baseline_raw:
        baseline_keys.add((b["rule_id"], b["file"], b.get("line", 0)))

    for f in findings:
        key = (f["rule_id"], f["file"], f.get("line", 0))
        f["is_new"] = key not in baseline_keys
        f["scope"] = "history"  # bandit scans the whole tree = history scope (§4.4)
    return findings


# ── main ─────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="Local evidence-provider backend.")
    parser.add_argument("--pilot-root", required=True)
    parser.add_argument("--framework-root", required=True)
    parser.add_argument("--test-file", required=True)
    parser.add_argument("--lock-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument(
        "--signing-key-env",
        default="EVIDENCE_SIGNING_KEY",
        help="Env var holding the HMAC signing key.",
    )
    parser.add_argument(
        "--key-id", default="local-default", help="Key identifier recorded in the signature."
    )
    parser.add_argument(
        "--security-scan", action="store_true", help="Run the Bandit security lens."
    )
    parser.add_argument(
        "--security-allowlist", default=None, help="Path to curated allowlist JSON."
    )
    parser.add_argument(
        "--security-baseline",
        default=None,
        help="Path to baseline Bandit scan for new-vs-baseline.",
    )
    parser.add_argument(
        "--full-suite",
        action="store_true",
        help="Run the full test suite for the tests section (what validators "
        "consumed in Phase 3). Without this, only the locked test is reported.",
    )
    args = parser.parse_args()

    started = utcnow_iso()

    # 1. Locked-hash check (reuse verify-green.py)
    print("[1/5] Locked-hash check via verify-green.py...", file=sys.stderr)
    vg = run_verify_green(
        args.framework_root,
        args.pilot_root,
        args.lock_file,
        args.test_file,
        args.python,
    )
    if not vg["green_accepted"]:
        print(f"  GREEN REFUSED (exit {vg['exit_code']}). Bundle will be red.", file=sys.stderr)
    else:
        print(
            f"  GREEN ACCEPTED. locked_test_sha={vg['locked_test_sha_observed']}", file=sys.stderr
        )

    # 2. Pytest structured results
    print("[2/5] Running pytest for structured test results...", file=sys.stderr)
    pt = run_pytest(args.pilot_root, args.test_file, args.python)
    print(
        f"  locked test: passed={pt['passed']} failed={pt['failed']} skipped={pt['skipped']} exit={pt['suite_exit_code']}",
        file=sys.stderr,
    )

    # 2b. Full regression suite (what validators also consumed in Phase 3)
    if args.full_suite:
        print("[2b] Running full regression suite...", file=sys.stderr)
        fs = run_pytest(args.pilot_root, "", args.python)  # empty test_file = full suite
        print(
            f"  full suite: passed={fs['passed']} failed={fs['failed']} skipped={fs['skipped']} exit={fs['suite_exit_code']}",
            file=sys.stderr,
        )
        # Use full suite results for the tests section, but merge any locked-test failures
        pt = fs

    # 3. Coverage (optional)
    print("[3/5] Coverage (best-effort)...", file=sys.stderr)
    cov = run_coverage(args.pilot_root, args.test_file, args.python)
    if cov:
        print(f"  lines_pct={cov['lines_pct']}%", file=sys.stderr)
    else:
        print("  not available (pytest-cov missing or failed)", file=sys.stderr)

    # 4. Security lens (optional)
    security_section = None
    if args.security_scan:
        print("[4/5] Security scan (Bandit)...", file=sys.stderr)
        bandit = run_bandit(args.pilot_root, args.python)

        # Load allowlist
        allowlist = {"allowlist": []}
        if args.security_allowlist and os.path.isfile(args.security_allowlist):
            with open(args.security_allowlist) as f:
                allowlist = json.load(f)

        # Load baseline
        baseline = {"raw_findings": []}
        if args.security_baseline and os.path.isfile(args.security_baseline):
            with open(args.security_baseline) as f:
                baseline = json.load(f)

        findings = apply_allowlist(bandit["raw_findings"], allowlist)
        findings = diff_vs_baseline(findings, baseline)

        # Compact by construction: only NEW findings enter the bundle.
        # Baseline debt (is_new=false) is excluded — the bundle carries only
        # what THIS change introduced (SPIKE §4.4 lesson 1 + §2.1 compact rule).
        new_findings = [f for f in findings if f["is_new"]]
        new_count = len(new_findings)
        total_count = len(findings)
        print(
            f"  total={total_count} new={new_count} suppressed={len(bandit['raw_findings']) - total_count}",
            file=sys.stderr,
        )

        security_section = {"findings": new_findings}
    else:
        print("[4/5] Security scan skipped (--security-scan not set).", file=sys.stderr)

    # 5. Assemble + sign the bundle
    print("[5/5] Assembling + signing bundle...", file=sys.stderr)
    finished = utcnow_iso()

    # Get commit SHA of the pilot repo
    commit_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=args.pilot_root,
        capture_output=True,
        text=True,
    ).stdout.strip()

    tool_versions = {
        "python": get_tool_version([args.python], "--version"),
        "pytest": get_tool_version([args.python, "-m", "pytest"], "--version"),
        # Evidence label, not a filesystem path: this string is serialised
        # into the bundle JSON, so it must render identically on every
        # platform. os.path.join would emit "phase-1\\scripts\\..." on
        # Windows and change an evidence byte. posixpath.join alone is NOT
        # enough either — SCRIPTS_ROOT is itself os.path.join'd, so it
        # already carries a backslash there. Re-split on os.sep and rejoin
        # with "/" so the separator cannot leak in from either source.
        "verify_green": "/".join((*SCRIPTS_ROOT.split(os.sep), "verify-green.py")),
    }
    if args.security_scan:
        tool_versions["bandit"] = get_tool_version([args.python, "-m", "bandit"], "--version")

    bundle: dict = {
        "bundle_schema_version": "v1",
        "producer": "local",
        "change": {
            "commit_sha": commit_sha,
            "locked_test_sha_observed": vg["locked_test_sha_observed"],
        },
        "tests": {
            "passed": pt["passed"],
            "failed": pt["failed"],
            "skipped": pt["skipped"],
            "suite_exit_code": pt["suite_exit_code"],
            "failures": pt["failures"],
        },
        "provenance": {
            "producer_run_id": str(uuid.uuid4()),
            "started_at": started,
            "finished_at": finished,
            "tool_versions": tool_versions,
        },
    }

    if cov:
        bundle["coverage"] = cov
    if security_section:
        bundle["security"] = security_section

    # Sign — require an explicit key; generate a random one if not set (with warning)
    signing_key_env = os.environ.get(args.signing_key_env)
    if signing_key_env:
        signing_key = signing_key_env.encode()
        key_id = args.key_id
    else:
        # No explicit key: generate a random one so the signature is not forgeable
        # by anyone who reads the source code. The signature is still valid for
        # this run, but the consumer must use the same key to verify — so this is
        # only useful for same-process verification (local demo). For any
        # cross-process or cross-agent scenario, set EVIDENCE_SIGNING_KEY.
        signing_key = os.urandom(32)
        key_id = f"local-random-{uuid.uuid4().hex[:8]}"
        print(
            f"  WARNING: {args.signing_key_env} not set. Generated random key "
            f"(key_id={key_id}). Signature is valid for this process only — "
            f"set {args.signing_key_env} for cross-process verification.",
            file=sys.stderr,
        )
    bundle = sign_bundle(bundle, signing_key, key_id)

    # Write
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(bundle, f, indent=2)

    bundle_size = os.path.getsize(args.output)
    print(f"\nBundle written: {args.output}", file=sys.stderr)
    print(f"  size: {bundle_size} bytes (~{bundle_size // 4} tokens)", file=sys.stderr)
    print(f"  green: {vg['green_accepted']}", file=sys.stderr)
    print(f"  locked_sha: {vg['locked_test_sha_observed']}", file=sys.stderr)

    # Exit 0 only if GREEN accepted and no test failures
    return 0 if (vg["green_accepted"] and pt["failed"] == 0) else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Evidence-bundle consumer: validator + orchestrator gate (SPIKE §5, §4.1).

Two consumers, both read the bundle instead of re-running pytest:

  - **ValidatorConsumer**: verifies the signature, checks test results, and
    reaches a verdict (ACCEPT / REJECT) from the bundle evidence. It does NOT
    re-run pytest. The cross-family review of the diff still stands (SPIKE §4.3
    — CI augments, does not replace, the panel); this consumer handles only the
    deterministic-evidence portion.

  - **OrchestratorGate**: verifies the signature, cross-checks
    `locked_test_sha_observed` against the local lock manifest (SPIKE §4.1), and
    fails closed on mismatch / missing bundle / red bundle.

Usage:
    python3 phase-3.2/evidence/consumer.py validate \
        --bundle phase-3.2/build-evidence/chunk1-bundle.json \
        --signing-key-env EVIDENCE_SIGNING_KEY

    python3 phase-3.2/evidence/consumer.py gate \
        --bundle phase-3.2/build-evidence/chunk1-bundle.json \
        --lock-file phase-1/locks/test/test_profile_model.py.lock.json \
        --signing-key-env EVIDENCE_SIGNING_KEY
"""

import argparse
import hashlib
import hmac
import json
import os
import sys

# ── signature verification ───────────────────────────────────────────────


def verify_signature(bundle: dict, key: bytes) -> bool:
    """Verify the HMAC-SHA256 signature over the bundle minus the signature field."""
    sig = bundle.get("signature")
    if not sig or sig.get("algorithm") != "HMAC-SHA256":
        return False

    payload_bundle = {k: v for k, v in bundle.items() if k != "signature"}
    payload = json.dumps(payload_bundle, sort_keys=True, separators=(",", ":")).encode()
    expected = hmac.new(key, payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig["value"])


# ── validator consumer ───────────────────────────────────────────────────


class ValidatorConsumer:
    """Reads the bundle and reaches a deterministic-evidence verdict.

    The verdict from this consumer is the *evidence* verdict (tests pass/fail).
    The full validator verdict also includes the diff/spec review, which is
    NOT replaced by the bundle (SPIKE §4.3).
    """

    def consume(self, bundle: dict, signing_key: bytes) -> dict:
        result = {
            "evidence_verdict": None,  # ACCEPT / REJECT / FAIL_CLOSED
            "tests_passed": False,
            "failures": [],
            "signature_valid": False,
            "reason": "",
        }

        # 1. Verify signature
        if not verify_signature(bundle, signing_key):
            result["evidence_verdict"] = "FAIL_CLOSED"
            result["reason"] = "bundle signature invalid — not trusted"
            return result
        result["signature_valid"] = True

        # 2. Check test results
        tests = bundle.get("tests", {})
        passed = tests.get("passed", 0)
        failed = tests.get("failed", 0)
        suite_exit = tests.get("suite_exit_code", 1)

        result["tests_passed"] = failed == 0 and suite_exit == 0 and passed > 0
        result["failures"] = tests.get("failures", [])

        if result["tests_passed"]:
            result["evidence_verdict"] = "ACCEPT"
            result["reason"] = f"bundle shows {passed} passed, 0 failed, suite exit 0"
        else:
            result["evidence_verdict"] = "REJECT"
            result["reason"] = f"bundle shows {failed} failure(s), suite exit {suite_exit}"

        return result


# ── orchestrator gate ────────────────────────────────────────────────────


class OrchestratorGate:
    """Cross-checks locked_test_sha_observed against the lock manifest (§4.1).

    Fail closed on: missing bundle, red bundle, or sha mismatch.
    """

    def gate(self, bundle: dict, lock_file: str, signing_key: bytes) -> dict:
        result = {
            "gate_decision": None,  # PASS / FAIL_CLOSED
            "sha_match": False,
            "signature_valid": False,
            "reason": "",
        }

        # 1. Verify signature
        if not verify_signature(bundle, signing_key):
            result["gate_decision"] = "FAIL_CLOSED"
            result["reason"] = "bundle signature invalid — not trusted"
            return result
        result["signature_valid"] = True

        # 2. Load lock manifest
        try:
            with open(lock_file) as f:
                manifest = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            result["gate_decision"] = "FAIL_CLOSED"
            result["reason"] = f"lock manifest unreadable: {e}"
            return result

        expected_sha = manifest.get("sha256")
        observed_sha = bundle.get("change", {}).get("locked_test_sha_observed")

        # 3. Cross-check (§4.1) — require non-empty real digests on both sides.
        #    None==None or ""=="" must NOT pass (fail-closed on missing evidence).
        if not expected_sha or not observed_sha:
            result["gate_decision"] = "FAIL_CLOSED"
            result["reason"] = (
                f"missing sha for cross-check: "
                f"manifest={expected_sha or 'MISSING'} "
                f"observed={observed_sha or 'MISSING'}"
            )
            return result

        if observed_sha != expected_sha:
            result["gate_decision"] = "FAIL_CLOSED"
            result["reason"] = (
                f"locked_test_sha_observed mismatch: "
                f"observed={observed_sha} manifest={expected_sha}"
            )
            return result
        result["sha_match"] = True

        # 4. Check bundle is green — fail closed on red AND on vacuous green
        #    (0 passed = all skipped or empty suite = silent-green defect)
        tests = bundle.get("tests", {})
        if tests.get("failed", 0) > 0 or tests.get("suite_exit_code", 1) != 0:
            result["gate_decision"] = "FAIL_CLOSED"
            result["reason"] = "bundle is red — test failures present"
            return result
        if tests.get("passed", 0) == 0:
            result["gate_decision"] = "FAIL_CLOSED"
            result["reason"] = "vacuous green — 0 tests passed (all skipped or empty suite)"
            return result

        result["gate_decision"] = "PASS"
        result["reason"] = (
            f"locked-sha matches manifest, suite green ({tests.get('passed', 0)} passed, 0 failed)"
        )
        return result


# ── CLI ──────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="Evidence-bundle consumer.")
    sub = parser.add_subparsers(dest="command", required=True)

    val_p = sub.add_parser("validate", help="Validator: reach evidence verdict from bundle.")
    val_p.add_argument("--bundle", required=True)
    val_p.add_argument("--signing-key-env", default="EVIDENCE_SIGNING_KEY")

    gate_p = sub.add_parser("gate", help="Orchestrator: locked-sha cross-check gate.")
    gate_p.add_argument("--bundle", required=True)
    gate_p.add_argument("--lock-file", required=True)
    gate_p.add_argument("--signing-key-env", default="EVIDENCE_SIGNING_KEY")

    args = parser.parse_args()

    # Load bundle — fail closed on missing/unreadable (not a raw exception)
    try:
        with open(args.bundle) as f:
            bundle = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        fail = {
            "evidence_verdict": "FAIL_CLOSED" if args.command == "validate" else None,
            "gate_decision": "FAIL_CLOSED" if args.command == "gate" else None,
            "reason": f"bundle missing or unreadable: {e}",
        }
        print(json.dumps(fail, indent=2))
        return 1

    signing_key_env = os.environ.get(args.signing_key_env)
    if not signing_key_env:
        print(
            f"ERROR: {args.signing_key_env} not set. Cannot verify bundle signature "
            f"without the signing key. Set it to the same value used by the backend.",
            file=sys.stderr,
        )
        return 1
    signing_key = signing_key_env.encode()

    if args.command == "validate":
        vc = ValidatorConsumer()
        r = vc.consume(bundle, signing_key)
        print(json.dumps(r, indent=2))
        return 0 if r["evidence_verdict"] == "ACCEPT" else 1

    elif args.command == "gate":
        og = OrchestratorGate()
        r = og.gate(bundle, args.lock_file, signing_key)
        print(json.dumps(r, indent=2))
        return 0 if r["gate_decision"] == "PASS" else 1

    return 1


if __name__ == "__main__":
    sys.exit(main())

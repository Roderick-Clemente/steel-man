#!/usr/bin/env python3
"""Orchestration script: the mechanical review pipeline.

This is the script that makes the process mechanical instead of ad hoc. It
runs the full cycle:

  step 1: produce evidence bundle (calls local_backend.py)
  step 2: run N validators via the shim (droid exec)
  step 3: check stray writes after each validator (KI-2 mitigation)
  step 4: parse verdicts from envelopes
  step 5: append telemetry rows to runs.jsonl
  step 6: report gate decision (any REJECT blocks; STOP only on error)

No asking. No waiting. No "should I merge?" questions. It runs, it reports,
it stops only if something breaks. The human reviews the output, not the
process.

Uses existing infrastructure:
  - tools/adapters/factory.py — vendor shim (Factory now, others later)
  - tools/run-with-model.sh — enforcement wrapper (refuses to run without --model)
  - phase-3.2/evidence/local_backend.py — the evidence producer

Usage:
    python3 tools/orchestrate-review.py \
        --framework-root /path/to/adversarial-sprint-dev \
        --pilot-root /path/to/quantum-bank \
        --pilot-python /path/to/quantum-bank/.venv/bin/python \
        --test-file test/test_profile_model.py \
        --lock-file phase-1/locks/test/test_profile_model.py.lock.json \
        --prompt-file phase-3.2/reviews/review-prompt.md \
        --review-output-dir phase-3.2/reviews/ \
        --validators grok-4.5:xai:grok-family,gemini-3.1-pro-preview:google:gemini-family \
        [--evidence-output phase-3.2/build-evidence/chunk1-bundle.json] \
        [--full-suite] [--security-scan] \
        [--security-allowlist phase-3.2/evidence/security_allowlist.json] \
        [--security-baseline phase-3.2/build-evidence/bandit-baseline.json] \
        [--auto-level high] \
        [--enabled-tools Read,Glob,Grep,LS,Execute]
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys

DROID_BIN = os.path.expanduser("~/.local/bin/droid")


def utcnow_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── step 1: produce evidence ─────────────────────────────────────────────

def step1_produce_evidence(args) -> dict:
    """Run local_backend.py to produce the evidence bundle."""
    print("\n" + "=" * 60)
    print("STEP 1: Produce evidence bundle")
    print("=" * 60)

    cmd = [
        args.pilot_python,
        os.path.join(args.framework_root, "phase-3.2", "evidence", "local_backend.py"),
        "--pilot-root", args.pilot_root,
        "--framework-root", args.framework_root,
        "--test-file", args.test_file,
        "--lock-file", args.lock_file,
        "--output", args.evidence_output,
        "--python", args.pilot_python,
    ]
    if args.full_suite:
        cmd.append("--full-suite")
    if args.security_scan:
        cmd.extend(["--security-scan"])
        if args.security_allowlist:
            cmd.extend(["--security-allowlist", args.security_allowlist])
        if args.security_baseline:
            cmd.extend(["--security-baseline", args.security_baseline])

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    print(result.stderr, file=sys.stderr)

    if result.returncode != 0:
        print(f"  ERROR: local_backend.py exited {result.returncode}", file=sys.stderr)
        return {"ok": False, "error": f"exit {result.returncode}"}

    bundle = json.load(open(args.evidence_output))
    tests = bundle.get("tests", {})
    print(f"  Bundle: {os.path.getsize(args.evidence_output)} bytes")
    print(f"  Tests: {tests.get('passed',0)} passed, {tests.get('failed',0)} failed")
    print(f"  Locked SHA: {bundle.get('change',{}).get('locked_test_sha_observed','NONE')}")
    print(f"  Green: {tests.get('failed',0) == 0 and tests.get('suite_exit_code',1) == 0}")

    return {"ok": True, "bundle": bundle}


# ── step 2: run validators ───────────────────────────────────────────────

def step2_run_validators(args, validators: list[dict]) -> list[dict]:
    """Run each validator via droid exec, capture envelope."""
    print("\n" + "=" * 60)
    print("STEP 2: Run cross-family validators")
    print("=" * 60)

    results = []
    os.makedirs(args.review_output_dir, exist_ok=True)

    for v in validators:
        model_id = v["model_id"]
        provider = v["provider"]
        family = v["family"]
        label = v.get("label", model_id)

        print(f"\n  [{label}] Running {model_id} ({family})...")

        envelope_path = os.path.join(args.review_output_dir, f"review-{label}-envelope.json")
        stderr_path = os.path.join(args.review_output_dir, f"review-{label}-stderr.log")

        cmd = [
            DROID_BIN, "exec",
            "--model", model_id,
            "--auto", args.auto_level,
            "--enabled-tools", args.enabled_tools,
            "--cwd", args.framework_root,
            "-f", args.prompt_file,
            "-o", "json",
        ]

        env = os.environ.copy()
        env["DROID_MODEL_ID"] = model_id

        with open(envelope_path, "w") as enf, open(stderr_path, "w") as errf:
            result = subprocess.run(
                cmd, stdout=enf, stderr=errf,
                cwd=args.framework_root, env=env,
                timeout=600,
            )

        v["envelope_path"] = envelope_path
        v["exit_code"] = result.returncode
        v["stderr_path"] = stderr_path

        # droid exec may exit non-zero but still write a valid envelope
        # (e.g. is_error=true for a provider failure). Read the envelope
        # regardless of exit code; only fail if the file is missing/invalid.
        try:
            envelope = json.load(open(envelope_path))
        except (json.JSONDecodeError, OSError) as e:
            print(f"    ERROR: envelope unreadable: {e} (exit {result.returncode})")
            v["ok"] = False
            results.append(v)
            continue

        v["envelope"] = envelope
        v["ok"] = True
        v["is_error"] = envelope.get("is_error", False)
        v["num_turns"] = envelope.get("num_turns", 0)
        v["input_tokens"] = envelope.get("usage", {}).get("input_tokens", 0)
        v["output_tokens"] = envelope.get("usage", {}).get("output_tokens", 0)
        v["duration_ms"] = envelope.get("duration_ms", 0)
        v["result_text"] = envelope.get("result", "")

        print(f"    turns={v['num_turns']} tokens_in={v['input_tokens']} tokens_out={v['output_tokens']} error={v['is_error']}")

        results.append(v)

    return results


# ── step 3: check stray writes ────────────────────────────────────────────

def step3_check_stray_writes(args, validator: dict) -> bool:
    """Check for stray writes after a validator run (KI-2 mitigation).

    Excludes the review output directory and known script artifacts — those
    are written by the orchestrator, not by the validator.
    """
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=args.framework_root,
        capture_output=True, text=True,
    )
    # Normalize the review output dir to a relative path for matching
    review_dir_rel = os.path.relpath(args.review_output_dir, args.framework_root)
    # Also exclude the orchestrator script itself
    orchestrator_rel = os.path.relpath(
        os.path.join(args.framework_root, "tools", "orchestrate-review.py"),
        args.framework_root,
    )

    stray_lines = []
    for line in result.stdout.strip().splitlines():
        # git status --porcelain format: "XY path"
        path = line[3:] if len(line) > 3 else line
        if path.startswith(review_dir_rel) or path == orchestrator_rel:
            continue  # expected output, not a stray write
        stray_lines.append(line)

    stray = "\n".join(stray_lines)
    if stray:
        print(f"    WARNING: stray writes detected after {validator['label']}:")
        print(f"    {stray}")
        validator["stray_writes"] = stray
        return False
    validator["stray_writes"] = None
    return True


# ── step 4: parse verdicts ───────────────────────────────────────────────

def step4_parse_verdicts(validators: list[dict]) -> list[dict]:
    """Extract the verdict from each validator's result text."""
    print("\n" + "=" * 60)
    print("STEP 4: Parse verdicts")
    print("=" * 60)

    verdict_pattern = re.compile(
        r'\b(ACCEPT|ACCEPT-WITH-NITS|REJECT(?:_IMPLEMENTATION|_TEST)?|REJECT|HUMAN_DECISION)\b',
        re.IGNORECASE
    )

    for v in validators:
        if not v.get("ok"):
            v["verdict"] = "ERROR"
            print(f"  {v['label']}: ERROR (run failed)")
            continue

        text = v.get("result_text", "")
        # Find the LAST occurrence (verdict is on the last line per prompt spec)
        matches = verdict_pattern.findall(text)
        if matches:
            v["verdict"] = matches[-1].upper()
        else:
            v["verdict"] = "UNKNOWN"
            print(f"  WARNING: no verdict found in {v['label']} output")

        print(f"  {v['label']}: {v['verdict']}")

    return validators


# ── step 5: append telemetry ─────────────────────────────────────────────

def step5_append_telemetry(args, validators: list[dict]):
    """Append telemetry rows to runs.jsonl."""
    print("\n" + "=" * 60)
    print("STEP 5: Append telemetry rows")
    print("=" * 60)

    runs_path = os.path.join(args.framework_root, "telemetry", "runs.jsonl")
    ts = utcnow_iso()

    with open(runs_path, "a") as f:
        for v in validators:
            row = {
                "schema_version": "v2",
                "ts": ts,
                "run_id": f"r-phase32-review-{v['label']}",
                "phase": args.phase,
                "branch": args.branch,
                "role": "validator",
                "model_id": v["model_id"],
                "provider": v["provider"],
                "family": v["family"],
                "providerLock": v["provider"],
                "apiProviderLock": v["provider"],
                "num_turns": v.get("num_turns", 0),
                "input_tokens": v.get("input_tokens", 0),
                "output_tokens": v.get("output_tokens", 0),
                "duration_ms": v.get("duration_ms", 0),
                "is_error": v.get("is_error", True),
                "decision": v.get("verdict", "UNKNOWN"),
                "evidence_source": "in-session",
                "envelope_path": v.get("envelope_path", ""),
            }
            f.write(json.dumps(row) + "\n")
            print(f"  Appended: {v['label']} -> {v.get('verdict', 'UNKNOWN')}")

    print(f"  Total rows appended: {len(validators)}")


# ── step 6: report gate decision ─────────────────────────────────────────

def step6_gate_decision(validators: list[dict]) -> str:
    """Aggregate verdicts and report the gate decision."""
    print("\n" + "=" * 60)
    print("STEP 6: Gate decision")
    print("=" * 60)

    verdicts = [v.get("verdict", "UNKNOWN") for v in validators]
    errors = [v for v in validators if not v.get("ok") or v.get("is_error", False)]
    rejects = [v for v in verdicts if v.startswith("REJECT")]
    accepts = [v for v in verdicts if v.startswith("ACCEPT")]
    humans = [v for v in verdicts if v == "HUMAN_DECISION"]
    unknowns = [v for v in verdicts if v == "UNKNOWN"]
    strays = [v for v in validators if v.get("stray_writes")]

    print(f"  Validators: {len(validators)}")
    print(f"  ACCEPT: {len(accepts)} | REJECT: {len(rejects)} | HUMAN_DECISION: {len(humans)} | ERROR: {len(errors)} | UNKNOWN: {len(unknowns)}")
    if strays:
        print(f"  Stray writes: {len(strays)} (KI-2 violation)")

    # Gate logic: any REJECT blocks, any ERROR stops, HUMAN_DECISION escalates
    if errors:
        gate = "STOP"
        reason = f"{len(errors)} validator(s) failed to run"
    elif rejects:
        gate = "REJECT"
        reason = f"{len(rejects)} validator(s) returned REJECT"
    elif unknowns:
        gate = "STOP"
        reason = f"{len(unknowns)} validator(s) had unparseable verdicts"
    elif strays:
        gate = "STOP"
        reason = f"{len(strays)} validator(s) wrote to the tree (KI-2 violation)"
    elif humans:
        gate = "HUMAN_DECISION"
        reason = f"{len(humans)} validator(s) returned HUMAN_DECISION"
    elif accepts:
        gate = "ACCEPT"
        nits = len([v for v in verdicts if v == "ACCEPT-WITH-NITS"])
        reason = f"All {len(accepts)} validator(s) ACCEPT" + (f" ({nits} with nits)" if nits else "")
    else:
        gate = "STOP"
        reason = "No valid verdicts"

    print(f"\n  GATE: {gate}")
    print(f"  REASON: {reason}")

    return gate


# ── main ─────────────────────────────────────────────────────────────────

def parse_validators(s: str) -> list[dict]:
    """Parse --validators string: model_id:provider:family[:label],..."""
    validators = []
    for entry in s.split(","):
        parts = entry.strip().split(":")
        if len(parts) < 3:
            print(f"ERROR: invalid validator entry '{entry}' (need model:provider:family)", file=sys.stderr)
            sys.exit(1)
        v = {
            "model_id": parts[0],
            "provider": parts[1],
            "family": parts[2],
            "label": parts[3] if len(parts) > 3 else parts[0],
        }
        validators.append(v)
    return validators


def main() -> int:
    parser = argparse.ArgumentParser(description="Orchestration script: mechanical review pipeline.")
    parser.add_argument("--framework-root", required=True)
    parser.add_argument("--pilot-root", required=True)
    parser.add_argument("--pilot-python", required=True)
    parser.add_argument("--test-file", required=True)
    parser.add_argument("--lock-file", required=True)
    parser.add_argument("--prompt-file", required=True)
    parser.add_argument("--review-output-dir", required=True)
    parser.add_argument("--validators", required=True,
                        help="Comma-separated: model_id:provider:family[:label],...")
    parser.add_argument("--evidence-output", default=None,
                        help="If set, step 1 produces a bundle. If not, skip step 1.")
    parser.add_argument("--full-suite", action="store_true")
    parser.add_argument("--security-scan", action="store_true")
    parser.add_argument("--security-allowlist", default=None)
    parser.add_argument("--security-baseline", default=None)
    parser.add_argument("--auto-level", default="high")
    parser.add_argument("--enabled-tools", default="Read,Glob,Grep,LS,Execute")
    parser.add_argument("--phase", default="phase-3.2")
    parser.add_argument("--branch", default=None,
                        help="Branch name for telemetry. Auto-detected if not set.")
    args = parser.parse_args()

    if not args.branch:
        args.branch = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=args.framework_root, capture_output=True, text=True,
        ).stdout.strip()

    validators = parse_validators(args.validators)

    # Step 1: produce evidence (optional)
    if args.evidence_output:
        ev = step1_produce_evidence(args)
        if not ev["ok"]:
            print(f"\nSTOP: step 1 failed: {ev['error']}", file=sys.stderr)
            return 1
    else:
        print("\nSTEP 1: Skipped (no --evidence-output)")

    # Step 2: run validators
    validators = step2_run_validators(args, validators)

    # Step 3: check stray writes after each
    print("\n" + "=" * 60)
    print("STEP 3: Check stray writes (KI-2 mitigation)")
    print("=" * 60)
    for v in validators:
        if v.get("ok"):
            step3_check_stray_writes(args, v)
            print(f"  {v['label']}: {'CLEAN' if not v.get('stray_writes') else 'STRAY WRITES'}")

    # Step 4: parse verdicts
    validators = step4_parse_verdicts(validators)

    # Step 5: append telemetry
    step5_append_telemetry(args, validators)

    # Step 6: gate decision
    gate = step6_gate_decision(validators)

    # Write summary
    summary = {
        "ts": utcnow_iso(),
        "branch": args.branch,
        "validators": [
            {
                "label": v["label"],
                "model": v["model_id"],
                "family": v["family"],
                "verdict": v.get("verdict", "ERROR"),
                "ok": v.get("ok", False),
                "tokens_in": v.get("input_tokens", 0),
                "tokens_out": v.get("output_tokens", 0),
                "stray_writes": v.get("stray_writes"),
            }
            for v in validators
        ],
        "gate": gate,
    }
    summary_path = os.path.join(args.review_output_dir, "review-summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'='*60}")
    print(f"SUMMARY written: {summary_path}")
    print(f"GATE: {gate}")
    print(f"{'='*60}")

    return 0 if gate in ("ACCEPT", "HUMAN_DECISION") else 1


if __name__ == "__main__":
    sys.exit(main())

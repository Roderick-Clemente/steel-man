#!/usr/bin/env python3
"""Orchestration script: the mechanical review pipeline.

This is the script that makes the process mechanical instead of ad hoc. It
runs the full cycle:

  step 1: produce evidence bundle (calls local_backend.py)
  step 2: run N validators via the shim (droid exec)
  step 3: check stray writes after each validator (KI-2 mitigation)
  step 4: parse verdicts from envelopes
  step 5: append telemetry rows to runs.jsonl
  step 6: report gate decision (any REJECT* or REPLAN blocks; STOP only on error)

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
        [--full-suite] [--full-suite-command "python -m pytest tests/ -q"] \
        [--security-scan] \
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
import time

# Invoked as ``python3 tools/orchestrate-review.py``, so sys.path[0] is already
# ``tools/`` and the layout roots (CHUNK-1-SPEC §2.1) import directly.
_TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

from sprint_loop.config import phase_path  # noqa: E402
from sprint_loop.evidence_timeout import local_backend_timeout_seconds  # noqa: E402
from sprint_loop.vocab import VALIDATOR_VERDICTS, tagged_line_pattern  # noqa: E402

DROID_BIN = os.path.expanduser("~/.local/bin/droid")

# How much of a validator's result text review-summary.json carries. Enough
# for a rejecting seat's reasoning to reach the seat that must act on it,
# bounded so the summary stays a summary.
REVIEW_FINDING_TEXT_LIMIT = 4000


def _import_adapter(framework_root: str):
    """Import the vendor-neutral adapter shim (OPERATING-RULES §14).

    Returns the factory adapter module's to_envelope function.
    """
    tools_dir = os.path.join(framework_root, "tools")
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    from adapters.factory import to_envelope

    return to_envelope


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
        phase_path(args.framework_root, "evidence-code", "local_backend.py"),
        "--pilot-root",
        args.pilot_root,
        "--framework-root",
        args.framework_root,
        "--test-file",
        args.test_file,
        "--lock-file",
        args.lock_file,
        "--output",
        args.evidence_output,
        "--python",
        args.pilot_python,
    ]
    full_suite_command = getattr(args, "full_suite_command", "") or ""
    full_suite_requested = bool(getattr(args, "full_suite", False))
    if full_suite_requested or full_suite_command:
        cmd.append("--full-suite")
    if full_suite_command:
        cmd.extend(["--full-suite-command", full_suite_command])
    if args.security_scan:
        cmd.extend(["--security-scan"])
        if args.security_allowlist:
            cmd.extend(["--security-allowlist", args.security_allowlist])
        if args.security_baseline:
            cmd.extend(["--security-baseline", args.security_baseline])

    timeout = local_backend_timeout_seconds(
        full_suite=full_suite_requested, security_scan=args.security_scan
    )
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        message = f"local_backend.py timed out after {timeout}s; evidence was not produced"
        print(f"  ERROR: {message}", file=sys.stderr)
        return {"ok": False, "error": message}
    print(result.stderr, file=sys.stderr)

    if result.returncode != 0:
        print(f"  ERROR: local_backend.py exited {result.returncode}", file=sys.stderr)
        return {"ok": False, "error": f"exit {result.returncode}"}

    bundle = json.load(open(args.evidence_output))
    tests = bundle.get("tests", {})
    print(f"  Bundle: {os.path.getsize(args.evidence_output)} bytes")
    print(f"  Tests: {tests.get('passed', 0)} passed, {tests.get('failed', 0)} failed")
    print(f"  Locked SHA: {bundle.get('change', {}).get('locked_test_sha_observed', 'NONE')}")
    print(f"  Green: {tests.get('failed', 0) == 0 and tests.get('suite_exit_code', 1) == 0}")

    # This step REWRITES the bundle at --evidence-output, so a bundle the
    # runner already produced with regression evidence is replaced by this
    # one. Refuse to hand validators a bundle missing the regression section
    # they were told to judge: absent tests.full_suite reads to a validator as
    # "no independent regression evidence", which is a REJECT it cannot
    # distinguish from a real regression.
    full_suite = tests.get("full_suite") or {}
    if (full_suite_requested or full_suite_command) and not full_suite:
        print(
            "  ERROR: --full-suite was requested but the bundle carries no "
            "tests.full_suite section",
            file=sys.stderr,
        )
        return {"ok": False, "error": "bundle has no tests.full_suite section"}
    if full_suite:
        print(
            f"  Full suite: {full_suite.get('passed', 0)} passed, "
            f"{full_suite.get('failed', 0)} failed, "
            f"exit {full_suite.get('suite_exit_code')}"
        )

    return {"ok": True, "bundle": bundle}


# ── step 2: run validators ───────────────────────────────────────────────


def capture_dirty_paths(framework_root: str) -> set[str]:
    """Capture the set of currently-dirty git paths as a baseline.

    This is the pre-run snapshot for the stray-write check (B1 fix #2).
    Only paths that are NEWLY dirty after a validator run are flagged —
    pre-existing dirty paths (untracked files, prior work) are excluded
    via set difference, not set equality.
    """
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=framework_root,
        capture_output=True,
        text=True,
    )
    paths = set()
    for line in result.stdout.strip().splitlines():
        if len(line) > 3:
            paths.add(line[3:])
    return paths


def step2_run_validators(args, validators: list[dict], to_envelope_fn) -> list[dict]:
    """Run each validator via droid exec, capture envelope."""
    print("\n" + "=" * 60)
    print("STEP 2: Run cross-family validators")
    print("=" * 60)

    results = []
    os.makedirs(args.review_output_dir, exist_ok=True)

    run_with_model = os.path.join(args.framework_root, "tools", "run-with-model.sh")

    for v in validators:
        model_id = v["model_id"]
        v["provider"]
        family = v["family"]
        label = v.get("label", model_id)

        print(f"\n  [{label}] Running {model_id} ({family})...")

        envelope_path = os.path.join(args.review_output_dir, f"review-{label}-envelope.json")
        stderr_path = os.path.join(args.review_output_dir, f"review-{label}-stderr.log")

        # Build the droid exec command, routed through run-with-model.sh (§14)
        # run-with-model.sh refuses to run without DROID_MODEL_ID set.
        # Resolve prompt file to absolute path (validator CWD may differ from framework root)
        prompt_file_abs = os.path.abspath(args.prompt_file)
        cmd = [
            run_with_model,
            DROID_BIN,
            "exec",
            "--model",
            model_id,
            "--auto",
            args.auto_level,
            "--enabled-tools",
            args.enabled_tools,
            "--cwd",
            args.validator_cwd,
            "-f",
            prompt_file_abs,
            "-o",
            "json",
        ]

        env = os.environ.copy()
        env["DROID_MODEL_ID"] = model_id

        # Transient retry logic (B1 fix #3): retry on 0 output tokens or ERROR
        # verdict, up to max_retries times with a short delay.
        max_retries = args.max_retries
        retry_delay = args.retry_delay
        attempt = 0
        v["retry_count"] = 0

        while True:
            with open(envelope_path, "w") as enf, open(stderr_path, "w") as errf:
                result = subprocess.run(
                    cmd,
                    stdout=enf,
                    stderr=errf,
                    cwd=args.validator_cwd,
                    env=env,
                    timeout=600,
                )

            v["envelope_path"] = envelope_path
            v["exit_code"] = result.returncode
            v["stderr_path"] = stderr_path

            # Use the adapter shim to parse the envelope (§14 — no raw field access)
            try:
                normalized = to_envelope_fn(envelope_path=envelope_path)
            except (json.JSONDecodeError, OSError, KeyError) as e:
                print(f"    ERROR: envelope unreadable: {e} (exit {result.returncode})")
                if attempt < max_retries:
                    attempt += 1
                    v["retry_count"] = attempt
                    print(
                        f"    Retry {attempt}/{max_retries} after {retry_delay}s (unreadable envelope)..."
                    )
                    time.sleep(retry_delay)
                    continue
                v["ok"] = False
                results.append(v)
                break

            v["ok"] = True
            v["is_error"] = normalized["is_error"]
            v["num_turns"] = normalized["num_turns"]
            v["input_tokens"] = normalized["usage"]["input"]
            v["output_tokens"] = normalized["usage"]["output"]
            v["cache_read_tokens"] = normalized["usage"]["cache_read"]
            v["thinking_tokens"] = normalized["usage"]["thinking"]
            v["duration_ms"] = normalized["duration_ms"]
            v["result_text"] = normalized["result_text"]
            v["adapter_model_id"] = normalized.get("model_id")
            v["adapter_family"] = normalized.get("family")

            # Check for transient failure: 0 output tokens or is_error
            is_transient = v["output_tokens"] == 0 or v["is_error"]

            if is_transient and attempt < max_retries:
                attempt += 1
                v["retry_count"] = attempt
                reason = "0 output tokens" if v["output_tokens"] == 0 else "is_error=true"
                print(
                    f"    Transient failure ({reason}), retry {attempt}/{max_retries} after {retry_delay}s..."
                )
                time.sleep(retry_delay)
                continue

            print(
                f"    turns={v['num_turns']} tokens_in={v['input_tokens']} tokens_out={v['output_tokens']} "
                f"cache_read={v['cache_read_tokens']} thinking={v['thinking_tokens']} "
                f"error={v['is_error']} retries={v['retry_count']}"
            )

            results.append(v)
            break

    return results


# ── step 3: check stray writes ────────────────────────────────────────────


def step3_check_stray_writes(args, validator: dict, baseline: set[str]) -> bool:
    """Check for stray writes after a validator run (KI-2 mitigation).

    Uses a pre-run baseline (B1 fix #2): only paths that are NEWLY dirty
    after the run are flagged. Pre-existing dirty paths (untracked files,
    prior work) are excluded via set difference, not set equality.
    """
    current = capture_dirty_paths(args.validator_cwd)

    # Normalize the review output dir to a relative path for matching
    review_dir_rel = os.path.relpath(args.review_output_dir, args.validator_cwd)

    # New paths = current - baseline (set difference)
    new_paths = current - baseline

    # Exclude expected orchestrator artifacts
    stray_paths = set()
    for path in new_paths:
        if path.startswith(review_dir_rel):
            continue  # expected output, not a stray write
        stray_paths.add(path)

    stray = "\n".join(sorted(stray_paths))
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
        tagged_line_pattern("VERDICT", VALIDATOR_VERDICTS),
        re.IGNORECASE | re.MULTILINE,
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
                "run_id": f"r-{args.run_label}-{v['label']}"
                if args.run_label
                else f"r-phase32-review-{v['label']}",
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
                "cache_read_tokens": v.get("cache_read_tokens", 0),
                "thinking_tokens": v.get("thinking_tokens", 0),
                "duration_ms": v.get("duration_ms", 0),
                "is_error": v.get("is_error", True),
                "decision": v.get("verdict", "UNKNOWN"),
                "evidence_source": args.evidence_source,
                "retry_count": v.get("retry_count", 0),
                "envelope_path": v.get("envelope_path", ""),
            }
            # Fairness-rule token fields (SPIKE §3.2)
            if args.evidence_source == "bundle":
                row["mcp_payload_tokens"] = args.mcp_payload_tokens or 0
            else:
                row["raw_test_output_tokens"] = args.raw_test_output_tokens or 0
            f.write(json.dumps(row) + "\n")
            print(
                f"  Appended: {v['label']} -> {v.get('verdict', 'UNKNOWN')} (retries={v.get('retry_count', 0)})"
            )

    print(f"  Total rows appended: {len(validators)}")


# ── step 6: report gate decision ─────────────────────────────────────────


def step6_gate_decision(validators: list[dict]) -> str:
    """Aggregate verdicts and report the gate decision.

    A ``REPLAN`` verdict blocks with ``gate=REJECT`` exactly like a
    ``REJECT*`` verdict; the per-validator verdicts the summary carries
    are what the runner's ``classify_rejection`` routes on.
    """
    print("\n" + "=" * 60)
    print("STEP 6: Gate decision")
    print("=" * 60)

    verdicts = [v.get("verdict", "UNKNOWN") for v in validators]
    errors = [v for v in validators if not v.get("ok") or v.get("is_error", False)]
    rejects = [v for v in verdicts if v.startswith("REJECT")]
    replans = [v for v in verdicts if v == "REPLAN"]
    accepts = [v for v in verdicts if v.startswith("ACCEPT")]
    humans = [v for v in verdicts if v == "HUMAN_DECISION"]
    unknowns = [v for v in verdicts if v == "UNKNOWN"]
    strays = [v for v in validators if v.get("stray_writes")]

    print(f"  Validators: {len(validators)}")
    print(
        f"  ACCEPT: {len(accepts)} | REJECT: {len(rejects)} | REPLAN: {len(replans)} | HUMAN_DECISION: {len(humans)} | ERROR: {len(errors)} | UNKNOWN: {len(unknowns)}"
    )
    if strays:
        print(f"  Stray writes: {len(strays)} (KI-2 violation)")

    # Gate logic: any REJECT or REPLAN blocks (the runner routes on the
    # preserved per-validator verdicts), any ERROR stops, HUMAN_DECISION
    # escalates. REPLAN must block: it is a plan-defect judgment the
    # runner re-enters planning for (KI-19); treating it as an accept
    # would be the exact silent-green defect its removal once masked.
    if errors:
        gate = "STOP"
        reason = f"{len(errors)} validator(s) failed to run"
    elif rejects or replans:
        gate = "REJECT"
        kinds = []
        if rejects:
            kinds.append("REJECT")
        if replans:
            kinds.append("REPLAN")
        reason = (
            f"{len(rejects) + len(replans)} validator(s) returned "
            f"{' or '.join(kinds)}"
        )
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
        reason = f"All {len(accepts)} validator(s) ACCEPT" + (
            f" ({nits} with nits)" if nits else ""
        )
    else:
        gate = "STOP"
        reason = "No valid verdicts"

    print(f"\n  GATE: {gate}")
    print(f"  REASON: {reason}")

    return gate, reason


# ── main ─────────────────────────────────────────────────────────────────


def parse_validators(s: str) -> list[dict]:
    """Parse --validators string: model_id:provider:family[:label],..."""
    validators = []
    for entry in s.split(","):
        parts = entry.strip().split(":")
        if len(parts) < 3:
            print(
                f"ERROR: invalid validator entry '{entry}' (need model:provider:family)",
                file=sys.stderr,
            )
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
    parser = argparse.ArgumentParser(
        description="Orchestration script: mechanical review pipeline."
    )
    parser.add_argument("--framework-root", required=True)
    parser.add_argument("--pilot-root", required=True)
    parser.add_argument("--pilot-python", required=True)
    parser.add_argument("--test-file", required=True)
    parser.add_argument("--lock-file", required=True)
    parser.add_argument("--prompt-file", required=True)
    parser.add_argument("--review-output-dir", required=True)
    parser.add_argument(
        "--validator-cwd",
        default=None,
        help="Working directory for validator droid exec calls. "
        "Defaults to --framework-root. Set to pilot repo for H-CI.",
    )
    parser.add_argument(
        "--validators", required=True, help="Comma-separated: model_id:provider:family[:label],..."
    )
    parser.add_argument(
        "--evidence-output",
        default=None,
        help="If set, step 1 produces a bundle. If not, skip step 1.",
    )
    parser.add_argument("--full-suite", action="store_true")
    parser.add_argument(
        "--full-suite-command",
        default="",
        help="The chunk's declared regression command, passed straight through "
        "to the evidence producer as --full-suite-command (implies --full-suite). "
        "Without it, --full-suite runs bare pytest from the pilot root.",
    )
    parser.add_argument("--security-scan", action="store_true")
    parser.add_argument("--security-allowlist", default=None)
    parser.add_argument("--security-baseline", default=None)
    parser.add_argument("--auto-level", default="high")
    parser.add_argument(
        "--enabled-tools",
        default=None,
        help="Comma-separated tool list. If not set, auto-derived from --treatment.",
    )
    parser.add_argument(
        "--treatment",
        action="store_true",
        help="Treatment mode (H-CI): validators get no Execute tool (KI-2 fix). "
        "Sets evidence_source=bundle and excludes Execute from enabled-tools.",
    )
    parser.add_argument(
        "--run-label",
        default=None,
        help="Label for this run (e.g., 'h-ci-run1-control'). Used in run_id for N-run A/B.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=2,
        help="Max retries on transient API failure (0 output tokens or ERROR). Default: 2.",
    )
    parser.add_argument(
        "--retry-delay", type=int, default=5, help="Delay in seconds between retries. Default: 5."
    )
    parser.add_argument("--phase", default="phase-3.2")
    parser.add_argument(
        "--branch", default=None, help="Branch name for telemetry. Auto-detected if not set."
    )
    parser.add_argument(
        "--evidence-source",
        default=None,
        help="evidence_source for telemetry rows. Auto-derived from --treatment if not set.",
    )
    parser.add_argument(
        "--mcp-payload-tokens",
        type=int,
        default=None,
        help="Bundle read token count (treatment arm, fairness rule).",
    )
    parser.add_argument(
        "--raw-test-output-tokens",
        type=int,
        default=None,
        help="Raw pytest output token count (control arm, fairness rule).",
    )
    parser.add_argument(
        "--allow-single-family",
        action="store_true",
        help="Allow a single-family validator panel. Default: refuse (PRD section 17.2).",
    )
    args = parser.parse_args()

    # Derive treatment-mode settings (B1 fix: parameterize KI-2 fix)
    if args.treatment:
        if args.evidence_source is None:
            args.evidence_source = "bundle"
        if args.enabled_tools is None:
            args.enabled_tools = "Read,Glob,Grep,LS"  # NO Execute — KI-2 fix
    else:
        if args.evidence_source is None:
            args.evidence_source = "in-session"
        if args.enabled_tools is None:
            args.enabled_tools = "Read,Glob,Grep,LS,Execute"  # control arm: validators run pytest

    if not args.branch:
        args.branch = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=args.framework_root,
            capture_output=True,
            text=True,
        ).stdout.strip()

    validators = parse_validators(args.validators)

    # Import the adapter shim (OPERATING-RULES §14)
    # Set validator CWD default (where validators run + stray writes checked)
    if not args.validator_cwd:
        args.validator_cwd = args.framework_root

    to_envelope_fn = _import_adapter(args.framework_root)

    # Cross-family enforcement (PRD section 17.2: >=2 distinct families required)
    families = {v["family"] for v in validators}
    if len(families) < 2 and not args.allow_single_family:
        print(
            f"ERROR: cross-family requirement not met. {len(families)} family(ies) "
            f"in panel ({families}). Need >=2 distinct families per PRD section 17.2. "
            f"Use --allow-single-family to override (not recommended).",
            file=sys.stderr,
        )
        return 1
    print(f"Cross-family check: {len(families)} families ({families}) — OK")
    print(f"Evidence source: {args.evidence_source} | Treatment: {args.treatment}")
    print(f"Enabled tools: {args.enabled_tools}")
    print(f"Validator CWD: {args.validator_cwd}")

    # Step 1: produce evidence (optional)
    if args.evidence_output:
        ev = step1_produce_evidence(args)
        if not ev["ok"]:
            print(f"\nSTOP: step 1 failed: {ev['error']}", file=sys.stderr)
            return 1
    else:
        print("\nSTEP 1: Skipped (no --evidence-output)")

    # Capture stray-write baseline BEFORE running validators (B1 fix #2)
    dirty_baseline = capture_dirty_paths(args.validator_cwd)
    if dirty_baseline:
        print(
            f"\n  Stray-write baseline: {len(dirty_baseline)} pre-existing dirty path(s) (will be excluded)"
        )

    # Step 2: run validators (via run-with-model.sh + adapter shim, with retry)
    validators = step2_run_validators(args, validators, to_envelope_fn)

    # Step 3: check stray writes after each (using baseline difference)
    print("\n" + "=" * 60)
    print("STEP 3: Check stray writes (KI-2 mitigation, baseline-aware)")
    print("=" * 60)
    for v in validators:
        if v.get("ok"):
            step3_check_stray_writes(args, v, dirty_baseline)
            print(f"  {v['label']}: {'CLEAN' if not v.get('stray_writes') else 'STRAY WRITES'}")

    # Step 4: parse verdicts
    validators = step4_parse_verdicts(validators)

    # Step 5: append telemetry
    step5_append_telemetry(args, validators)

    # Step 6: gate decision
    gate, gate_reason = step6_gate_decision(validators)

    # Write summary
    summary = {
        "ts": utcnow_iso(),
        "branch": args.branch,
        "evidence_source": args.evidence_source,
        "treatment": args.treatment,
        "run_label": args.run_label,
        # The gate's reason string, so the runner's BackendResult carries
        # the verdict-kind breakdown (e.g. "1 validator(s) returned
        # REPLAN") instead of the generic "reject gate returned" the
        # summary historically left for it.
        "note": gate_reason,
        "validators": [
            {
                "label": v["label"],
                "model": v["model_id"],
                "family": v["family"],
                "verdict": v.get("verdict", "ERROR"),
                "ok": v.get("ok", False),
                "tokens_in": v.get("input_tokens", 0),
                "tokens_out": v.get("output_tokens", 0),
                "cache_read": v.get("cache_read_tokens", 0),
                "thinking": v.get("thinking_tokens", 0),
                "retry_count": v.get("retry_count", 0),
                "stray_writes": v.get("stray_writes"),
                "envelope_path": v.get("envelope_path", ""),
                # A REJECT_TEST verdict is only actionable if the seat
                # that must fix the test can read WHY it was rejected;
                # the summary is the only artifact the runner parses.
                "finding_text": (v.get("result_text") or "")[:REVIEW_FINDING_TEXT_LIMIT],
            }
            for v in validators
        ],
        "gate": gate,
    }
    summary_path = os.path.join(args.review_output_dir, "review-summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'=' * 60}")
    print(f"SUMMARY written: {summary_path}")
    print(f"GATE: {gate}")
    print(f"{'=' * 60}")

    return 0 if gate in ("ACCEPT", "HUMAN_DECISION") else 1


if __name__ == "__main__":
    sys.exit(main())

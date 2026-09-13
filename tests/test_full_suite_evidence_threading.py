"""The regression suite the chunk declares must reach the validators.

Observed failure this pins. A live run produced a correct bundle
(``tests.full_suite`` present), then the validation step re-produced the
bundle at the *same path* without the full-suite flag and overwrote it. Both
validator seats read a bundle whose only test section was ``scope:
locked-test`` and both returned ``REJECT_IMPLEMENTATION``: absent
``tests.full_suite`` means there is no independent regression evidence, and
the executor's prose ("35/35") is not evidence. The refusal was correct.

Two further defects made the same chunk's regression gate vacuous even when
the section was present:

  - full-suite mode ran bare ``pytest`` from the pilot root instead of the
    command the chunk declares, so a pilot whose tests live in a subdirectory
    collected nothing (pytest exit 5);
  - ``failed == 0`` on a run that collected nothing read as a pass, in the
    producer, in the validator consumer and in the orchestrator gate.
"""

from __future__ import annotations
import __future__ as future_flags

import hashlib
import hmac
import importlib.util
import json
import os
import subprocess
import sys
import types

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TOOLS = os.path.join(_REPO, "tools")
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)

from sprint_loop import per_chunk  # noqa: E402
from sprint_loop.backends import LocalBackend  # noqa: E402
from sprint_loop.state import (  # noqa: E402
    ChunkState,
    GateDecision,
    Role,
    RoleAssignment,
    RunState,
)


def _load_producer_module():
    """Load ``tools/phase-3.2-evidence/local_backend.py`` (hyphenated dir).

    The module carries a PEP-604 (``dict | None``) annotation that
    ``test_layout_paths_chunk2.py`` pins as a known, tolerated failure under
    Python < 3.10, so a plain import cannot work on the repo's own
    interpreter. Compiling with PEP-563 enabled defers annotation evaluation
    without touching the module source.
    """
    path = os.path.join(_TOOLS, "phase-3.2-evidence", "local_backend.py")
    with open(path) as f:
        src = f.read()
    code = compile(
        src, path, "exec", flags=future_flags.annotations.compiler_flag, dont_inherit=True
    )
    mod = types.ModuleType("evidence_local_backend_fs")
    mod.__file__ = path
    exec(code, mod.__dict__)
    return mod


def _load_consumer_module():
    path = os.path.join(_TOOLS, "phase-3.2-evidence", "consumer.py")
    spec = importlib.util.spec_from_file_location("evidence_consumer_fs", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_orchestrator_module():
    path = os.path.join(_TOOLS, "orchestrate-review.py")
    spec = importlib.util.spec_from_file_location("orchestrate_review_fs", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── fixtures: a pilot whose tests bare pytest would not collect ──────────


def _make_pilot(tmp_path, *, break_one: bool = False):
    """A pilot with the locked test at the root and two more in ``suite/``.

    Bare ``pytest`` from the pilot root collects nothing here: the pilot's own
    ``pytest.ini`` sets ``testpaths`` to a directory that holds no tests, and
    ``testpaths`` applies exactly when no target is named on the command line.
    That is the shape the live pilot hit — the regression gate ran nothing and
    reported success.
    """
    pilot = tmp_path / "pilot"
    (pilot / "suite").mkdir(parents=True)
    (pilot / "api").mkdir(parents=True)
    (pilot / "api" / "app.py").write_text("VALUE = 1\n")
    (pilot / "pytest.ini").write_text("[pytest]\ntestpaths = api\n")
    (pilot / "locked_check.py").write_text(
        "def test_locked():\n    assert True\n",
    )
    (pilot / "suite" / "test_existing.py").write_text(
        "def test_one():\n    assert True\n\n"
        "def test_two():\n    assert %s\n" % ("False" if break_one else "True"),
    )
    return pilot


def _sign(bundle: dict, key: bytes) -> dict:
    payload = {k: v for k, v in bundle.items() if k != "signature"}
    digest = hmac.new(
        key, json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(), hashlib.sha256
    ).hexdigest()
    bundle["signature"] = {"algorithm": "HMAC-SHA256", "value": digest, "key_id": "test"}
    return bundle


def _bundle_with(tests: dict) -> dict:
    return {
        "bundle_schema_version": "v1",
        "producer": "local",
        "change": {"commit_sha": "a" * 40, "locked_test_sha_observed": "b" * 64},
        "tests": tests,
    }


_GREEN_LOCKED = {
    "passed": 6,
    "failed": 0,
    "skipped": 0,
    "suite_exit_code": 0,
    "scope": "locked-test",
}

# The exact shape the live pilot produced: bare pytest from the root collected
# nothing, so the regression section looked green while running no tests.
_VACUOUS_FULL_SUITE = {
    "passed": 0,
    "failed": 0,
    "skipped": 0,
    "suite_exit_code": 5,
    "failures": [],
    "scope": "full-suite",
}


# ── defect 1: the review step must not strip the regression section ──────


def test_review_step_does_not_replace_a_bundle_that_has_full_suite_with_one_that_does_not(
    tmp_path, monkeypatch
):
    """The exact observed failure, pinned at the LocalBackend boundary."""
    bundle_path = tmp_path / "c1-bundle.json"
    review_dir = tmp_path / "reviews"
    bundle_path.write_text(
        json.dumps(
            _bundle_with({**_GREEN_LOCKED, "full_suite": {**_VACUOUS_FULL_SUITE, "passed": 29}})
        )
    )
    monkeypatch.setenv("EVIDENCE_SIGNING_KEY", "k")
    captured: dict = {}

    def _fake_orchestrator(argv, **kwargs):
        # Stands in for orchestrate-review.py step 1, which re-produces the
        # bundle at --evidence-output. The producer only writes a full_suite
        # section when it is told to run the regression suite.
        captured["argv"] = argv
        out = argv[argv.index("--evidence-output") + 1]
        bundle = json.loads(open(out).read())
        if "--full-suite-command" not in argv and "--full-suite" not in argv:
            bundle["tests"].pop("full_suite", None)
        with open(out, "w") as f:
            json.dump(bundle, f)
        os.makedirs(review_dir, exist_ok=True)
        with open(os.path.join(review_dir, "review-summary.json"), "w") as f:
            json.dump({"gate": "ACCEPT", "validators": [{"verdict": "ACCEPT"}]}, f)
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(subprocess, "run", _fake_orchestrator)

    result = LocalBackend().validate(
        chunk={
            "test_file": "locked_check.py",
            "lock_file": str(tmp_path / "lock.json"),
            "review_output_dir": str(review_dir),
        },
        evidence_bundle=str(bundle_path),
        framework_root=_REPO,
        pilot_root=str(tmp_path),
        pilot_python=sys.executable,
        signing_key_env="EVIDENCE_SIGNING_KEY",
        validators=["m:p:f:m"],
        run_label="r-1",
        prompt_template_path=str(tmp_path / "prompt.md"),
        full_suite_command="python -m pytest suite -q",
    )

    assert result.gate is GateDecision.ACCEPT
    argv = captured["argv"]
    assert "--full-suite-command" in argv
    assert argv[argv.index("--full-suite-command") + 1] == "python -m pytest suite -q"
    # What the validators actually read.
    reread = json.loads(bundle_path.read_text())
    assert "full_suite" in reread["tests"], (
        "the review step replaced a bundle carrying tests.full_suite with one "
        "that does not — validators would see no regression evidence"
    )


def test_local_backend_omits_the_flag_when_the_chunk_declares_no_regression_command(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("EVIDENCE_SIGNING_KEY", "k")
    review_dir = tmp_path / "reviews"
    captured: dict = {}

    def _fake_orchestrator(argv, **kwargs):
        captured["argv"] = argv
        os.makedirs(review_dir, exist_ok=True)
        with open(os.path.join(review_dir, "review-summary.json"), "w") as f:
            json.dump({"gate": "ACCEPT", "validators": []}, f)
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(subprocess, "run", _fake_orchestrator)
    LocalBackend().validate(
        chunk={
            "test_file": "locked_check.py",
            "lock_file": str(tmp_path / "lock.json"),
            "review_output_dir": str(review_dir),
        },
        evidence_bundle=str(tmp_path / "b.json"),
        framework_root=_REPO,
        pilot_root=str(tmp_path),
        pilot_python=sys.executable,
        signing_key_env="EVIDENCE_SIGNING_KEY",
        validators=["m:p:f:m"],
        run_label="r-1",
        prompt_template_path=str(tmp_path / "prompt.md"),
    )
    assert "--full-suite-command" not in captured["argv"]


def test_run_validators_threads_the_chunks_regression_command(tmp_path, monkeypatch):
    """A caller that forgets to pass the command still gets it (derived)."""
    chunk = ChunkState(
        chunk_id="c1",
        scope="s",
        observable_criteria=["c"],
        allowed_files=["app.py"],
        locked_test_files=["test/test_health.py"],
        commands=[
            "python -m pytest test/test_health.py -v",
            "python -m pytest suite -q",
        ],
        rollback="r",
        lock_manifest_path=str(tmp_path / "lock.json"),
        locked_test_sha="a" * 64,
    )
    rs = RunState(
        run_id="r-fs",
        started_at="2026-08-16T00:00:00Z",
        framework_root=str(tmp_path / "fw"),
        pilot_root=str(tmp_path / "pilot"),
        pilot_python=sys.executable,
        validators=[
            RoleAssignment(
                role=Role.VALIDATOR,
                pinned_model_id="grok-4.5",
                pinned_family="grok-family",
                pinned_provider="xai",
                enabled_tools="Read,Glob,Grep,LS",
            )
        ],
    )
    os.makedirs(rs.pilot_root, exist_ok=True)
    chunk.evidence_bundle_path = str(tmp_path / "c1-bundle.json")
    with open(chunk.evidence_bundle_path, "w") as f:
        json.dump(_bundle_with(dict(_GREEN_LOCKED)), f)

    captured: dict = {}

    class _CapturingBackend:
        def __init__(self, dry_run: bool = False):
            pass

        def validate(self, **kwargs):
            captured.update(kwargs)
            return per_chunk.BackendResult(gate=GateDecision.ACCEPT, reason="captured")

    monkeypatch.setattr(per_chunk, "LocalBackend", _CapturingBackend)
    per_chunk.run_validators(
        chunk, rs, evidence_output_dir=str(tmp_path / "evidence"), dry_run=True
    )
    assert captured["full_suite_command"] == "python -m pytest suite -q"


def test_orchestrator_step1_fails_closed_when_the_reproduced_bundle_has_no_full_suite(
    tmp_path, monkeypatch
):
    orchestrator = _load_orchestrator_module()
    out = tmp_path / "bundle.json"

    def _fake_producer(argv, **kwargs):
        with open(out, "w") as f:
            json.dump(_bundle_with(dict(_GREEN_LOCKED)), f)
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(subprocess, "run", _fake_producer)
    args = types.SimpleNamespace(
        pilot_python=sys.executable,
        framework_root=_REPO,
        pilot_root=str(tmp_path),
        test_file="locked_check.py",
        lock_file=str(tmp_path / "lock.json"),
        evidence_output=str(out),
        full_suite=False,
        full_suite_command="python -m pytest suite -q",
        security_scan=False,
        security_allowlist=None,
        security_baseline=None,
    )
    result = orchestrator.step1_produce_evidence(args)
    assert result["ok"] is False
    assert "tests.full_suite" in result["error"]


def test_orchestrator_step1_passes_the_command_to_the_producer(tmp_path, monkeypatch):
    orchestrator = _load_orchestrator_module()
    out = tmp_path / "bundle.json"
    captured: dict = {}

    def _fake_producer(argv, **kwargs):
        captured["argv"] = argv
        with open(out, "w") as f:
            json.dump(
                _bundle_with({**_GREEN_LOCKED, "full_suite": {**_VACUOUS_FULL_SUITE, "passed": 2, "suite_exit_code": 0}}),
                f,
            )
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(subprocess, "run", _fake_producer)
    args = types.SimpleNamespace(
        pilot_python=sys.executable,
        framework_root=_REPO,
        pilot_root=str(tmp_path),
        test_file="locked_check.py",
        lock_file=str(tmp_path / "lock.json"),
        evidence_output=str(out),
        full_suite=False,
        full_suite_command="python -m pytest suite -q",
        security_scan=False,
        security_allowlist=None,
        security_baseline=None,
    )
    assert orchestrator.step1_produce_evidence(args)["ok"] is True
    argv = captured["argv"]
    assert "--full-suite" in argv
    assert argv[argv.index("--full-suite-command") + 1] == "python -m pytest suite -q"


def test_produce_evidence_passes_the_command_to_the_producer(tmp_path, monkeypatch):
    chunk = ChunkState(
        chunk_id="c1",
        scope="s",
        observable_criteria=["c"],
        allowed_files=["app.py"],
        locked_test_files=["locked_check.py"],
        commands=["python -m pytest suite -q"],
        rollback="r",
        lock_manifest_path=str(tmp_path / "lock.json"),
        locked_test_sha="a" * 64,
    )
    captured: dict = {}

    def _fake_step(cmd, label, timeout=0):
        captured["cmd"] = cmd
        raise RuntimeError("stop after argv capture")

    monkeypatch.setattr(per_chunk, "_run_step", _fake_step)
    with pytest.raises(RuntimeError):
        per_chunk.produce_evidence(
            chunk,
            framework_root=_REPO,
            pilot_root=str(tmp_path),
            pilot_python=sys.executable,
            evidence_output_path=str(tmp_path / "b.json"),
            full_suite_command="python -m pytest suite -q",
        )
    cmd = captured["cmd"]
    assert "--full-suite" in cmd
    assert cmd[cmd.index("--full-suite-command") + 1] == "python -m pytest suite -q"


# ── defect 2: the declared command runs, not bare pytest ─────────────────


def test_declared_command_selectors_survive_and_reporting_flags_are_reimposed():
    producer = _load_producer_module()
    assert producer.pytest_args_from_command("python -m pytest suite -q") == ["suite"]
    assert producer.pytest_args_from_command(
        "/usr/bin/python3 -m pytest tests/unit -q -k 'not slow' --tb=short -p no:randomly"
    ) == ["tests/unit", "-k", "not slow", "-p", "no:randomly"]
    # ``--tb line`` spends its value on the following token.
    assert producer.pytest_args_from_command("pytest tests --tb line -v") == ["tests"]


def test_a_command_that_does_not_invoke_pytest_is_refused():
    producer = _load_producer_module()
    with pytest.raises(ValueError) as exc:
        producer.pytest_args_from_command("make regression")
    assert "pytest" in str(exc.value)


def test_producer_runs_the_declared_command_where_bare_pytest_collects_nothing(tmp_path):
    producer = _load_producer_module()
    pilot = _make_pilot(tmp_path)

    bare = producer.run_pytest(str(pilot), "", sys.executable)
    assert bare["passed"] == 0
    assert bare["suite_exit_code"] == producer.PYTEST_EXIT_NO_TESTS_COLLECTED

    declared = producer.run_pytest_command(
        str(pilot), "python -m pytest suite -q", sys.executable
    )
    assert declared["passed"] == 2
    assert declared["failed"] == 0
    assert declared["suite_exit_code"] == 0
    assert "suite" in declared["command"]


def test_producer_reports_real_failures_from_the_declared_command(tmp_path):
    producer = _load_producer_module()
    pilot = _make_pilot(tmp_path, break_one=True)
    declared = producer.run_pytest_command(
        str(pilot), "python -m pytest suite -q", sys.executable
    )
    assert declared["passed"] == 1
    assert declared["failed"] == 1
    assert producer.regression_refusal_reason(declared).startswith("1 failure(s)")


# ── defect 3: collecting nothing is not a pass ───────────────────────────


def test_producer_refuses_a_regression_run_that_collected_nothing():
    producer = _load_producer_module()
    reason = producer.regression_refusal_reason(dict(_VACUOUS_FULL_SUITE))
    assert reason, "exit 5 with zero collected tests must not read as a pass"
    assert "5" in reason
    assert "no tests" in reason


@pytest.mark.parametrize("exit_code", [2, 3, 4])
def test_producer_refuses_pytest_usage_and_internal_errors(exit_code):
    producer = _load_producer_module()
    reason = producer.regression_refusal_reason(
        {"passed": 3, "failed": 0, "skipped": 0, "suite_exit_code": exit_code}
    )
    assert str(exit_code) in reason


def test_producer_accepts_a_genuinely_green_regression_run():
    producer = _load_producer_module()
    assert (
        producer.regression_refusal_reason(
            {"passed": 29, "failed": 0, "skipped": 1, "suite_exit_code": 0}
        )
        == ""
    )


def test_consumer_rejects_a_regression_run_that_collected_nothing():
    consumer = _load_consumer_module()
    key = b"k"
    bundle = _sign(_bundle_with({**_GREEN_LOCKED, "full_suite": dict(_VACUOUS_FULL_SUITE)}), key)
    result = consumer.ValidatorConsumer().consume(bundle, key)
    assert result["evidence_verdict"] == "REJECT"
    assert "5" in result["reason"]
    assert "collected no tests" in result["reason"]


def test_gate_fails_closed_on_a_regression_run_that_collected_nothing(tmp_path):
    consumer = _load_consumer_module()
    key = b"k"
    lock_file = tmp_path / "lock.json"
    lock_file.write_text(json.dumps({"sha256": "b" * 64}))
    bundle = _sign(_bundle_with({**_GREEN_LOCKED, "full_suite": dict(_VACUOUS_FULL_SUITE)}), key)
    result = consumer.OrchestratorGate().gate(bundle, str(lock_file), key)
    assert result["gate_decision"] == "FAIL_CLOSED"
    assert "full-suite regression" in result["reason"]
    assert "5" in result["reason"]


def test_a_green_regression_run_still_passes_and_stays_distinguishable(tmp_path):
    consumer = _load_consumer_module()
    key = b"k"
    lock_file = tmp_path / "lock.json"
    lock_file.write_text(json.dumps({"sha256": "b" * 64}))
    tests = {
        **_GREEN_LOCKED,
        "full_suite": {
            "passed": 29,
            "failed": 0,
            "skipped": 0,
            "suite_exit_code": 0,
            "scope": "full-suite",
            "command": "python -m pytest suite -v",
        },
    }
    bundle = _sign(_bundle_with(tests), key)

    verdict = consumer.ValidatorConsumer().consume(bundle, key)
    assert verdict["evidence_verdict"] == "ACCEPT"
    assert "full suite 29 passed" in verdict["reason"]
    assert consumer.OrchestratorGate().gate(bundle, str(lock_file), key)["gate_decision"] == "PASS"

    # The two scopes are separate objects with their own counters, so a
    # validator cannot read the locked-test result as the regression result.
    assert bundle["tests"]["scope"] == "locked-test"
    assert bundle["tests"]["full_suite"]["scope"] == "full-suite"
    assert bundle["tests"]["passed"] != bundle["tests"]["full_suite"]["passed"]

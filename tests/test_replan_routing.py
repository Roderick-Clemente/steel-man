"""Tests for the REPLAN route back into the plan loop (KI-19 fast follow).

A chunk validator's ``REPLAN`` verdict is directed at the PLAN the chunk
was derived from, not at the code (``REJECT_IMPLEMENTATION``) or the
locked test (``REJECT_TEST``). Neither chunk-local seat can fix that, so
the runner must:

  - stop the chunk fail-closed (no executor / test-designer re-fire),
  - preserve the rejecting evidence (superseded-replan archive),
  - carry the validator's finding into the planner prompt,
  - re-derive every chunk's state against the revised plan, and
  - stay bounded: ``replan_budget`` replans per run (default 1), with
    exhaustion escalating to HUMAN_DECISION and a distinct exit code.

These tests pin the routing, the feedback that reaches the planner, the
evidence that must survive the superseded round, the bound on the
replan, the re-chunking that invalidates state derived from the
rejected plan, and the telemetry that keeps replan rounds countable.
"""

from __future__ import annotations

import json
import os
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TOOLS = os.path.join(_REPO, "tools")
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)

import pytest  # noqa: E402
from conftest import (  # noqa: E402
    _load_runner_module,
    _observed,
    _run_state,
    _stub_loop,
)
from sprint_loop import per_chunk  # noqa: E402
from sprint_loop.backends import BackendResult  # noqa: E402
from sprint_loop.config import Config  # noqa: E402
from sprint_loop.state import (  # noqa: E402
    ChunkState,
    ChunkStatus,
    GateDecision,
)


def _chunk() -> ChunkState:
    return ChunkState(
        chunk_id="c-rt",
        scope="read devices without naming a home",
        observable_criteria=["devices are readable without an explicit identifier"],
        locked_test_files=["test/test_devices.py"],
        commands=["/usr/bin/true -m pytest test/test_devices.py -v"],
        accepted_assertion="devices readable without identifier",
    )


_REPLAN_FINDING = (
    "The chunk spec's test strategy cannot prove the criterion under the "
    "current plan: the plan names a unit test for an end-to-end behaviour, "
    "so the plan has to change before any chunk of it can be verified."
)


def _replan_result() -> BackendResult:
    return BackendResult(
        gate=GateDecision.REJECT,
        reason="1 validator(s) returned REPLAN",
        validators=[
            {
                "label": "grok-4.5",
                "model": "grok-4.5",
                "family": "grok-family",
                "verdict": "REPLAN",
                "finding_text": _REPLAN_FINDING,
                "envelope_path": "/tmp/reviews/review-grok-4.5-envelope.json",
            },
            {
                "label": "gemini-3.1-pro-preview",
                "model": "gemini-3.1-pro-preview",
                "family": "gemini-family",
                "verdict": "ACCEPT",
            },
        ],
    )


def _accept_result() -> BackendResult:
    return BackendResult(
        gate=GateDecision.ACCEPT,
        reason="all 2 validator(s) ACCEPT",
        validators=[{"label": "grok-4.5", "verdict": "ACCEPT"},
                    {"label": "gemini-3.1-pro-preview", "verdict": "ACCEPT"}],
    )


# ── classification ───────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "verdicts,expected",
    [
        (["REPLAN"], "plan"),
        (["REPLAN", "ACCEPT"], "plan"),
        (["ACCEPT", "ACCEPT"], ""),
        (["REPLAN", "REJECT_TEST"], "plan"),
        (["REPLAN", "REJECT_IMPLEMENTATION"], "plan"),
        # A REPLAN seat dominates: its finding is about the root artifact
        # the other two verdicts derive from, and neither executor nor
        # test-designer can satisfy it.
        (["REJECT_TEST", "ACCEPT"], "test"),
        (["REJECT", "ACCEPT"], "implementation"),
        ([], ""),
    ],
)
def test_classify_rejection_routes_replan(verdicts, expected):
    assert (
        per_chunk.classify_rejection([{"verdict": v} for v in verdicts]) == expected
    )


# ── routing: the chunk stops fail-closed on REPLAN ───────────────────────


def test_replan_stops_the_chunk_and_stashes_the_finding(tmp_path, monkeypatch):
    mod = _load_runner_module()
    pilot = tmp_path / "pilot"
    (pilot / "test").mkdir(parents=True)
    (pilot / "test" / "test_devices.py").write_text(
        "def test_devices():\n    assert True\n"
    )
    rs = _run_state(str(pilot))
    chunk = _chunk()
    observed = _observed()
    _stub_loop(
        mod, monkeypatch, chunk, tmp_path, observed,
        stub_render_executor_prompt=True,
    )
    monkeypatch.setattr(mod, "run_validators", lambda *a, **k: _replan_result())

    chunk = mod.run_chunk_with_retries(rs, chunk, str(tmp_path / "ev"), False, Config())

    assert chunk.status == ChunkStatus.REPLAN
    assert chunk.rejection_kind == "plan"
    assert rs.replans_spent == 1
    assert _REPLAN_FINDING in "\n".join(rs.replan_feedback)
    # Fail-closed: the most expensive seats were not re-invoked against a
    # plan the panel has rejected. The test existed on disk, so the
    # designer never fired; the executor fired exactly once (first
    # attempt) and was not retried.
    assert observed["invoke_executor"] == 1
    assert observed["invoke_test_designer"] == 0
    # Implementation feedback is irrelevant on the plan route and must
    # not bleed into any later seat prompt.
    assert chunk.rejection_feedback == []


def test_round_2_replan_exhausts_the_budget(tmp_path, monkeypatch):
    """With one replan already charged (replan_budget=1), a second REPLAN
    escalates straight to HUMAN_DECISION — the runner never re-enters
    planning on a spent budget."""
    mod = _load_runner_module()
    pilot = tmp_path / "pilot"
    (pilot / "test").mkdir(parents=True)
    (pilot / "test" / "test_devices.py").write_text(
        "def test_devices():\n    assert True\n"
    )
    rs = _run_state(str(pilot))
    rs.replan_budget = 1
    rs.replans_spent = 1  # the replan round already happened
    chunk = _chunk()
    observed = _observed()
    _stub_loop(
        mod, monkeypatch, chunk, tmp_path, observed,
        stub_render_executor_prompt=True,
    )
    monkeypatch.setattr(mod, "run_validators", lambda *a, **k: _replan_result())

    chunk = mod.run_chunk_with_retries(rs, chunk, str(tmp_path / "ev"), False, Config())

    assert chunk.status == ChunkStatus.HUMAN_DECISION
    assert chunk.rejection_kind == "plan"
    assert rs.replans_spent == 1  # nothing extra was charged
    assert "replan budget exhausted" in rs.status_message


def test_zero_replan_budget_fails_closed_immediately(tmp_path, monkeypatch):
    mod = _load_runner_module()
    pilot = tmp_path / "pilot"
    (pilot / "test").mkdir(parents=True)
    (pilot / "test" / "test_devices.py").write_text(
        "def test_devices():\n    assert True\n"
    )
    rs = _run_state(str(pilot))
    rs.replan_budget = 0
    chunk = _chunk()
    observed = _observed()
    _stub_loop(
        mod, monkeypatch, chunk, tmp_path, observed,
        stub_render_executor_prompt=True,
    )
    monkeypatch.setattr(mod, "run_validators", lambda *a, **k: _replan_result())

    chunk = mod.run_chunk_with_retries(rs, chunk, str(tmp_path / "ev"), False, Config())

    assert chunk.status == ChunkStatus.HUMAN_DECISION
    assert "replan budget exhausted" in rs.status_message


# ── the finding reaches the planner's prompt rendering ───────────────────


def test_format_replan_rejection_feedback_carries_the_rejecting_seats_reasoning():
    text = per_chunk.format_replan_rejection_feedback(_replan_result())
    assert _REPLAN_FINDING in text
    assert "REPLAN" in text
    assert "grok-4.5" in text
    # The ACCEPTing seat has no plan-defect finding.
    assert "gemini-3.1-pro-preview" not in text


def test_format_replan_rejection_feedback_falls_back_to_the_gate_reason():
    res = BackendResult(
        gate=GateDecision.REJECT,
        reason="dry-run: simulated REPLAN",
        validators=[{"label": "v1", "verdict": "REPLAN"}],
    )
    assert per_chunk.format_replan_rejection_feedback(res) == "dry-run: simulated REPLAN"


def test_runner_renders_the_replan_finding_into_the_planner_prompt(tmp_path):
    mod = _load_runner_module()
    rs = _run_state(str(tmp_path / "pilot"))
    rs.replan_feedback = [per_chunk.format_replan_rejection_feedback(_replan_result())]
    rs.plan_round = 2
    out = tmp_path / "plan-prompt-r2.md"
    rendered = mod.render_to_file(
        "planner",
        {
            "pilot_spec_path": "(none)",
            "plan_output_path": str(tmp_path / "plan.md"),
            "authored_chunks": "(none supplied)",
            "prior_findings": "(first round — no prior findings)",
            "replan_feedback": mod._format_replan_feedback(rs.replan_feedback),
        },
        str(out),
    )
    text = (tmp_path / "plan-prompt-r2.md").read_text()
    assert _REPLAN_FINDING in text
    assert "{{" not in text
    assert rendered.endswith("plan-prompt-r2.md")


# ── evidence preservation ────────────────────────────────────────────────


def test_replan_archives_the_rejecting_review_and_bundle(tmp_path, monkeypatch):
    mod = _load_runner_module()
    pilot = tmp_path / "pilot"
    (pilot / "test").mkdir(parents=True)
    (pilot / "test" / "test_devices.py").write_text(
        "def test_devices():\n    assert True\n"
    )
    rs = _run_state(str(pilot))
    chunk = _chunk()
    observed = _observed()
    _stub_loop(
        mod, monkeypatch, chunk, tmp_path, observed,
        stub_render_executor_prompt=True,
        produce_bundle=False,
    )
    monkeypatch.setattr(mod, "run_validators", lambda *a, **k: _replan_result())

    ev = tmp_path / "ev"
    (ev / "reviews").mkdir(parents=True)
    with open(str(ev / "reviews" / "review-summary.json"), "w") as f:
        json.dump({"gate": "REJECT"}, f)
    bundle_path = ev / "c-rt-bundle.json"
    bundle_path.write_text('{"change": {"locked_test_sha_observed": "x"}}')
    chunk.evidence_bundle_path = str(bundle_path)

    mod.run_chunk_with_retries(rs, chunk, str(ev), False, Config())

    dest = ev / "superseded-replan-round1"
    assert (dest / "reviews" / "review-summary.json").is_file()
    assert (dest / "c-rt-bundle.json").is_file()
    # The live locations were vacated so the re-derived chunk round
    # cannot shadow the rejecting evidence.
    assert not (ev / "reviews").exists()
    assert not bundle_path.exists()


# ── end-to-end through the run loop with stubbed seats ───────────────────


_FW_DIRS = (
    "tools/sprint_loop",
    "tools/phase-1-scripts",
    "tools/phase-3.2-evidence",
    "tools/orchestrate-review.py",
    "telemetry",
)


def _build_framework(tmp_path, *, extra_cfg: dict | None = None) -> str:
    fw = tmp_path / "fw"
    for dirname in _FW_DIRS:
        target = fw / dirname
        if "orchestrate-review.py" in dirname:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("# stub")
        else:
            target.mkdir(parents=True, exist_ok=True)
    (tmp_path / "pilot").mkdir()
    cfg_payload = {
        "framework_root": str(fw),
        "pilot_root": str(tmp_path / "pilot"),
        "pilot_python": "/usr/bin/python3",
        "validators": [
            "grok-4.5:xai:grok-family:grok-4.5",
            "gemini-3.1-pro-preview:google:gemini-family:gemini-3.1-pro-preview",
        ],
    }
    if extra_cfg:
        cfg_payload.update(extra_cfg)
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps(cfg_payload))
    chunks_path = tmp_path / "chunks.json"
    chunks_path.write_text(
        json.dumps(
            {
                "chunks": [
                    {
                        "chunk_id": "c1",
                        "scope": "read devices without naming a home",
                        "observable_criteria": [
                            "devices readable without an identifier"
                        ],
                        "allowed_files": ["app.py"],
                        "locked_test_files": ["test/test_devices.py"],
                        "commands": ["pytest test/test_devices.py -v"],
                        "accepted_assertion": "devices readable without identifier",
                    }
                ]
            }
        )
    )
    return str(fw)


def test_replan_reruns_planning_and_rechunks_before_continuing(tmp_path, monkeypatch):
    """The real run loop with stubbed droid seats: round 1 REPLANs, the
    runner re-enters plan → review → reconcile, re-derives the chunk
    list (nothing derived from the rejected plan is reused), and only
    then re-runs the chunk."""
    mod = _load_runner_module("sprint_loop_runner_replan_loop")
    fw = _build_framework(tmp_path)

    results = [_replan_result(), _accept_result()]
    monkeypatch.setattr(mod, "run_validators", lambda *a, **k: results.pop(0))

    batches = []
    real_load_chunks = mod.load_chunks

    def spy_load_chunks(rs_arg, chunks_file):
        loaded = real_load_chunks(rs_arg, chunks_file)
        batches.append(loaded)
        return loaded

    monkeypatch.setattr(mod, "load_chunks", spy_load_chunks)

    rc = mod.main(
        [
            "--config", str(tmp_path / "cfg.json"),
            "--chunks-file", str(tmp_path / "chunks.json"),
            "--dry-run",
            "--non-interactive",
            "--run-label", "replan-loop",
        ]
    )

    assert rc == 0
    # Chunk state invalidation: the chunk list was re-derived from the
    # chunks file after the replan, with fresh ChunkState objects.
    assert len(batches) == 2
    assert len(batches[0]) == 1
    assert len(batches[1]) == 1
    assert batches[1] is not batches[0]
    assert batches[1][0] is not batches[0][0]

    # Evidence: the plan-loop round-indexed paths keep both rounds, the
    # replan round's planner prompt carries the validator's finding, and
    # the planner seat rows distinguish first plan from replan round.
    ev_root = os.path.join(fw, "evidence", "phase-4.5", "build-evidence")
    run_dir = list(os.path.join(ev_root, d) for d in os.listdir(ev_root))[0]
    assert os.path.isfile(os.path.join(run_dir, "plan-r1.md"))
    assert os.path.isfile(os.path.join(run_dir, "plan-r2.md"))
    prompt_2 = open(os.path.join(run_dir, "plan-prompt-r2.md")).read()
    assert _REPLAN_FINDING in prompt_2

    rows = [
        json.loads(line)
        for line in open(os.path.join(fw, "telemetry", "runs.jsonl")).read().splitlines()
    ]
    planner_rows = [r for r in rows if r.get("role") == "planner"]
    assert [r["phase_step"] for r in planner_rows] == ["plan", "plan-replan"]
    run_rows = [r for r in rows if r.get("role") == "run"]
    assert run_rows[-1]["exit_code"] == 0
    assert run_rows[-1]["replans_spent"] == 1
    assert run_rows[-1]["replan_budget"] == 1
    assert run_rows[-1]["chunk_statuses"][0]["status"] == "ACCEPTED"


def test_replan_exhaustion_exits_7_end_to_end(tmp_path, monkeypatch):
    """Repeated REPLAN against every replanned plan must end in a
    distinct non-zero exit (7) with a reason naming replan-budget
    exhaustion, a checkpoint, and round-indexed evidence — not spin."""
    mod = _load_runner_module("sprint_loop_runner_replan_e2e")
    fw = _build_framework(tmp_path, extra_cfg={"replan_budget": 1})

    calls = {"n": 0}

    def always_replan(*a, **k):
        calls["n"] += 1
        assert calls["n"] < 10, "REPLAN routing did not terminate"
        return _replan_result()

    monkeypatch.setattr(mod, "run_validators", always_replan)

    rc = mod.main(
        [
            "--config", str(tmp_path / "cfg.json"),
            "--chunks-file", str(tmp_path / "chunks.json"),
            "--dry-run",
            "--non-interactive",
            "--run-label", "replan-bound",
        ]
    )

    assert rc == 7
    rows = [
        json.loads(line)
        for line in open(os.path.join(fw, "telemetry", "runs.jsonl")).read().splitlines()
    ]
    run_rows = [r for r in rows if r.get("role") == "run"]
    assert run_rows, "no role=run summary row"
    assert "replan budget exhausted" in run_rows[-1]["status_message"]
    assert run_rows[-1]["replans_spent"] == 1

    ev_root = os.path.join(fw, "evidence", "phase-4.5", "build-evidence")
    run_dir = list(os.path.join(ev_root, d) for d in os.listdir(ev_root))[0]
    assert os.path.isfile(os.path.join(run_dir, "checkpoint.json"))
    assert os.path.isfile(os.path.join(run_dir, "plan-r2.md"))
    # The second REPLAN's rejecting evidence was archived round-indexed.
    assert os.path.isdir(os.path.join(run_dir, "c1", "superseded-replan-round2"))


def test_help_documents_the_replan_exit_codes_and_budget(tmp_path):
    mod = _load_runner_module("sprint_loop_runner_replan_help")
    help_text = mod._runner_argparser().format_help()
    # argparse reflows the epilog, so pin the content, not the spacing.
    assert "Exit codes" in help_text
    assert "REPLAN budget exhausted" in help_text
    assert "AWAITING_HUMAN_DECISION" in help_text
    assert "--replan-budget" in mod._format_build_config_help_synthetic()

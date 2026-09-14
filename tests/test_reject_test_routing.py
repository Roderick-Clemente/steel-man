"""Tests for REJECT_TEST routing back to the test-designer seat.

The validator panel can reject a chunk for two materially different
reasons. ``REJECT_IMPLEMENTATION`` means the locked test is a fair
contract and the code fails it — the executor runs again.
``REJECT_TEST`` means the locked test does not lock what the chunk
claims — regenerating the test is the only thing that can fix that, so
re-running the executor against the same test burns the most expensive
seat in the pipeline for nothing.

These tests pin the routing, the feedback that reaches the designer, the
evidence that must survive a superseded round, the bound on the bounce,
and the telemetry that keeps the two cycles countable apart.
"""

from __future__ import annotations

import json
import os
import subprocess
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
from sprint_loop.per_chunk import (  # noqa: E402
    archive_superseded_test,
    classify_rejection,
    format_test_rejection_feedback,
    render_test_designer_prompt,
)
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


_FINDING = (
    "Every assertion in the locked test passes an explicit identifier, so the "
    "criterion about reading devices without naming a home is unproven."
)


def _reject_test_result() -> BackendResult:
    return BackendResult(
        gate=GateDecision.REJECT,
        reason="1 validator(s) returned REJECT",
        validators=[
            {
                "label": "grok-4.5",
                "model": "grok-4.5",
                "family": "grok-family",
                "verdict": "REJECT_TEST",
                "finding_text": _FINDING,
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


def _reject_impl_result() -> BackendResult:
    return BackendResult(
        gate=GateDecision.REJECT,
        reason="1 validator(s) returned REJECT",
        validators=[
            {
                "label": "grok-4.5",
                "model": "grok-4.5",
                "family": "grok-family",
                "verdict": "REJECT_IMPLEMENTATION",
                "finding_text": "criterion 2 is not met by the diff",
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
        (["ACCEPT", "ACCEPT"], ""),
        (["ACCEPT", "ACCEPT-WITH-NITS"], ""),
        (["REJECT_TEST"], "test"),
        (["REJECT_TEST", "ACCEPT"], "test"),
        (["REJECT_TEST", "reject_test"], "test"),
        (["REJECT_IMPLEMENTATION"], "implementation"),
        (["REJECT"], "implementation"),
        # A mixed panel routes to the implementation: one seat holding the
        # test to be a fair contract means the code has to change.
        (["REJECT_TEST", "REJECT_IMPLEMENTATION"], "implementation"),
        ([], ""),
    ],
)
def test_classify_rejection(verdicts, expected):
    assert classify_rejection([{"verdict": v} for v in verdicts]) == expected


# ── routing ──────────────────────────────────────────────────────────────


def test_reject_test_invokes_test_designer_and_not_the_executor(tmp_path, monkeypatch):
    mod = _load_runner_module()
    pilot = tmp_path / "pilot"
    (pilot / "test").mkdir(parents=True)
    rs = _run_state(str(pilot))
    chunk = _chunk()
    observed = _observed()
    _stub_loop(
        mod, monkeypatch, chunk, tmp_path, observed,
        stub_render_executor_prompt=True,
    )
    monkeypatch.setattr(mod, "run_validators", lambda *a, **k: _accept_result())

    # The state the runner is in after a REJECT_TEST verdict.
    chunk.rejection_kind = "test"
    chunk.test_design_feedback = [_FINDING]
    (pilot / "test" / "test_devices.py").write_text("def test_devices():\n    assert True\n")
    observed["invoke_test_designer"] = 1  # a designer already ran this chunk

    mod.run_chunk_inner(rs, chunk, str(tmp_path / "ev"), False, Config())

    assert observed["invoke_test_designer"] == 2  # the designer ran again
    assert observed["invoke_executor"] == 0  # the expensive seat did not
    assert observed["td_phase_steps"][-1] == "test-design-rerun"


def test_reject_implementation_invokes_executor_and_not_the_test_designer(
    tmp_path, monkeypatch
):
    mod = _load_runner_module()
    pilot = tmp_path / "pilot"
    (pilot / "test").mkdir(parents=True)
    (pilot / "test" / "test_devices.py").write_text("def test_devices():\n    assert True\n")
    rs = _run_state(str(pilot))
    chunk = _chunk()
    observed = _observed()
    _stub_loop(
        mod, monkeypatch, chunk, tmp_path, observed,
        stub_render_executor_prompt=True,
    )
    monkeypatch.setattr(mod, "run_validators", lambda *a, **k: _accept_result())

    chunk.rejection_kind = "implementation"
    chunk.rejection_feedback = ["criterion 2 is not met by the diff"]

    mod.run_chunk_inner(rs, chunk, str(tmp_path / "ev"), False, Config())

    assert observed["invoke_test_designer"] == 0
    assert observed["invoke_executor"] == 1


def test_validation_step_classifies_the_verdict_onto_the_chunk(tmp_path, monkeypatch):
    mod = _load_runner_module()
    pilot = tmp_path / "pilot"
    (pilot / "test").mkdir(parents=True)
    (pilot / "test" / "test_devices.py").write_text("def test_devices():\n    assert True\n")
    rs = _run_state(str(pilot))
    chunk = _chunk()
    observed = _observed()
    _stub_loop(
        mod, monkeypatch, chunk, tmp_path, observed,
        stub_render_executor_prompt=True,
    )
    monkeypatch.setattr(mod, "run_validators", lambda *a, **k: _reject_test_result())

    mod.run_chunk_inner(rs, chunk, str(tmp_path / "ev"), False, Config())

    assert chunk.gate_decision == GateDecision.REJECT
    assert chunk.rejection_kind == "test"
    assert _FINDING in chunk.test_design_feedback[0]


# ── the finding reaches the designer ─────────────────────────────────────


def test_format_test_rejection_feedback_carries_the_rejecting_seats_reasoning():
    text = format_test_rejection_feedback(_reject_test_result())
    assert _FINDING in text
    assert "REJECT_TEST" in text
    assert "grok-4.5" in text
    # The ACCEPTing seat is not a test-design finding.
    assert "gemini-3.1-pro-preview" not in text


def test_format_test_rejection_feedback_falls_back_to_the_gate_reason():
    res = BackendResult(
        gate=GateDecision.REJECT,
        reason="dry-run: simulated REJECT_TEST",
        validators=[{"label": "v1", "verdict": "REJECT_TEST"}],
    )
    assert format_test_rejection_feedback(res) == "dry-run: simulated REJECT_TEST"


def test_test_designer_prompt_carries_the_validator_finding(tmp_path):
    rs = _run_state(str(tmp_path / "pilot"))
    chunk = _chunk()
    chunk.test_design_feedback = [format_test_rejection_feedback(_reject_test_result())]
    out = tmp_path / "td-prompt.md"
    render_test_designer_prompt(chunk, rs, "the pilot spec body", str(out))
    text = out.read_text()

    assert _FINDING in text
    assert "{{" not in text


def test_reject_test_round_renders_the_finding_into_the_designers_prompt(
    tmp_path, monkeypatch
):
    """End-to-end through the retry loop: the finding the panel raised
    must be in the prompt file the re-fired designer was handed."""
    mod = _load_runner_module()
    pilot = tmp_path / "pilot"
    (pilot / "test").mkdir(parents=True)
    (pilot / "test" / "test_devices.py").write_text("def test_devices():\n    assert True\n")
    rs = _run_state(str(pilot))
    chunk = _chunk()
    observed = _observed()
    _stub_loop(
        mod, monkeypatch, chunk, tmp_path, observed,
        stub_render_executor_prompt=True,
    )
    results = [_reject_test_result(), _accept_result()]
    monkeypatch.setattr(mod, "run_validators", lambda *a, **k: results.pop(0))

    ev = tmp_path / "ev"
    chunk = mod.run_chunk_with_retries(rs, chunk, str(ev), False, Config())

    assert chunk.status == ChunkStatus.ACCEPTED
    assert chunk.test_design_retry_count == 1
    prompt = (ev / "c-rt-td-prompt.md").read_text()
    assert _FINDING in prompt


# ── evidence preservation ────────────────────────────────────────────────


def test_archive_superseded_test_moves_test_and_review_aside(tmp_path):
    rs = _run_state(str(tmp_path / "pilot"))
    chunk = _chunk()
    test_abs = tmp_path / "pilot" / "test" / "test_devices.py"
    test_abs.parent.mkdir(parents=True)
    test_abs.write_text("the superseded locked test\n")
    ev = tmp_path / "ev"
    (ev / "reviews").mkdir(parents=True)
    (ev / "reviews" / "review-summary.json").write_text('{"gate": "REJECT"}')

    moved = archive_superseded_test(chunk, rs, evidence_output_dir=str(ev), round_index=0)

    dest = ev / "superseded-test-round0"
    assert (dest / "test_devices.py").read_text() == "the superseded locked test\n"
    assert (dest / "reviews" / "review-summary.json").is_file()
    # The test must LEAVE the pilot tree — its absence is what makes the
    # designer auto-fire path re-author it.
    assert not test_abs.exists()
    assert not (ev / "reviews").exists()
    assert set(moved) == {"locked_test", "reviews"}


def test_superseded_test_and_rejecting_review_survive_a_reject_test_cycle(
    tmp_path, monkeypatch
):
    mod = _load_runner_module()
    pilot = tmp_path / "pilot"
    (pilot / "test").mkdir(parents=True)
    (pilot / "test" / "test_devices.py").write_text("the first locked test\n")
    rs = _run_state(str(pilot))
    chunk = _chunk()
    observed = _observed()
    _stub_loop(
        mod, monkeypatch, chunk, tmp_path, observed,
        stub_render_executor_prompt=True,
    )
    ev = tmp_path / "ev"

    def fake_run_validators(*a, **k):
        # Stand in for the backend writing the panel's review artifacts.
        os.makedirs(str(ev / "reviews"), exist_ok=True)
        with open(str(ev / "reviews" / "review-summary.json"), "w") as f:
            json.dump({"gate": "REJECT", "round": len(results)}, f)
        return results.pop(0)

    results = [_reject_test_result(), _accept_result()]
    monkeypatch.setattr(mod, "run_validators", fake_run_validators)

    mod.run_chunk_with_retries(rs, chunk, str(ev), False, Config())

    # Round index = the bounce that superseded the test.
    dest = ev / "superseded-test-round1"
    assert (dest / "test_devices.py").read_text() == "the first locked test\n"
    rejecting = json.loads((dest / "reviews" / "review-summary.json").read_text())
    assert rejecting["gate"] == "REJECT"
    # The accepting round's own review is still in place, unshadowed.
    assert (ev / "reviews" / "review-summary.json").is_file()


# ── the retry is bounded ─────────────────────────────────────────────────


def test_reject_test_every_round_terminates_on_the_test_design_budget(
    tmp_path, monkeypatch
):
    mod = _load_runner_module()
    pilot = tmp_path / "pilot"
    (pilot / "test").mkdir(parents=True)
    (pilot / "test" / "test_devices.py").write_text("def test_devices():\n    assert True\n")
    rs = _run_state(str(pilot))
    chunk = _chunk()
    observed = _observed()
    _stub_loop(
        mod, monkeypatch, chunk, tmp_path, observed,
        stub_render_executor_prompt=True,
    )
    calls = {"n": 0}

    def always_reject_test(*a, **k):
        calls["n"] += 1
        assert calls["n"] < 10, "REJECT_TEST routing did not terminate"
        return _reject_test_result()

    monkeypatch.setattr(mod, "run_validators", always_reject_test)

    chunk = mod.run_chunk_with_retries(rs, chunk, str(tmp_path / "ev"), False, Config())

    assert chunk.status == ChunkStatus.HUMAN_DECISION
    assert chunk.test_design_retry_count == rs.retry_threshold
    assert "test-design retry budget exhausted" in rs.status_message
    # Only the first round paid the executor; the bounce spent the
    # test-design budget and re-validated the preserved implementation.
    assert observed["invoke_executor"] == 1
    assert calls["n"] == rs.retry_threshold + 1


def test_reject_test_does_not_consume_the_executor_retry_budget(tmp_path, monkeypatch):
    """A test-design bounce followed by a REJECT_IMPLEMENTATION must still
    leave the executor its own retry."""
    mod = _load_runner_module()
    pilot = tmp_path / "pilot"
    (pilot / "test").mkdir(parents=True)
    (pilot / "test" / "test_devices.py").write_text("def test_devices():\n    assert True\n")
    rs = _run_state(str(pilot))
    chunk = _chunk()
    observed = _observed()
    _stub_loop(
        mod, monkeypatch, chunk, tmp_path, observed,
        regenerated_test_is_green=False,
        stub_render_executor_prompt=True,
    )
    results = [_reject_test_result(), _reject_impl_result(), _accept_result()]
    monkeypatch.setattr(mod, "run_validators", lambda *a, **k: results.pop(0))

    chunk = mod.run_chunk_with_retries(rs, chunk, str(tmp_path / "ev"), False, Config())

    assert chunk.status == ChunkStatus.ACCEPTED
    assert chunk.test_design_retry_count == 1
    assert chunk.retry_count == 1
    assert results == []


def test_reject_test_exhaustion_exits_non_zero_end_to_end(tmp_path, monkeypatch):
    """The run must end with a non-zero exit and a reason naming
    test-design exhaustion, not spin."""
    mod = _load_runner_module("sprint_loop_runner_reject_test_e2e")
    fw = tmp_path / "fw"
    (fw / "tools" / "sprint_loop").mkdir(parents=True)
    (fw / "tools/phase-1-scripts").mkdir(parents=True)
    (fw / "tools/phase-3.2-evidence").mkdir(parents=True)
    (fw / "tools" / "orchestrate-review.py").write_text("# stub")
    (fw / "telemetry").mkdir()
    (tmp_path / "pilot").mkdir()

    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(
        json.dumps(
            {
                "framework_root": str(fw),
                "pilot_root": str(tmp_path / "pilot"),
                "pilot_python": "/usr/bin/python3",
                "validators": [
                    "grok-4.5:xai:grok-family:grok-4.5",
                    "gemini-3.1-pro-preview:google:gemini-family:gemini-3.1-pro-preview",
                ],
            }
        )
    )
    chunks_path = tmp_path / "chunks.json"
    chunks_path.write_text(
        json.dumps(
            {
                "chunks": [
                    {
                        "chunk_id": "c1",
                        "scope": "read devices without naming a home",
                        "observable_criteria": ["devices readable without an identifier"],
                        "allowed_files": ["app.py"],
                        "locked_test_files": ["test/test_devices.py"],
                        "commands": ["pytest test/test_devices.py -v"],
                        "accepted_assertion": "devices readable without identifier",
                    }
                ]
            }
        )
    )

    calls = {"n": 0}

    def always_reject_test(*a, **k):
        calls["n"] += 1
        assert calls["n"] < 10, "REJECT_TEST routing did not terminate"
        return _reject_test_result()

    monkeypatch.setattr(mod, "run_validators", always_reject_test)

    rc = mod.main(
        [
            "--config", str(cfg_path),
            "--chunks-file", str(chunks_path),
            "--dry-run",
            "--non-interactive",
            "--run-label", "reject-test-bound",
        ]
    )

    assert rc != 0
    rows = [
        json.loads(line)
        for line in (fw / "telemetry" / "runs.jsonl").read_text().splitlines()
    ]
    run_rows = [r for r in rows if r.get("role") == "run"]
    assert run_rows, "no role=run summary row"
    assert "test-design retry budget exhausted" in run_rows[-1]["status_message"]


# ── telemetry distinguishes the two cycles ───────────────────────────────


def test_run_summary_row_separates_test_design_from_executor_cycles(tmp_path):
    mod = _load_runner_module()
    rs = _run_state(str(tmp_path), framework_root=_REPO)
    c1 = ChunkState(chunk_id="c-rt", scope="s")
    c1.status = ChunkStatus.HUMAN_DECISION
    c1.gate_decision = GateDecision.REJECT
    c1.retry_count = 0
    c1.test_design_retry_count = 2
    c1.rejection_kind = "test"
    c2 = ChunkState(chunk_id="c-impl", scope="s")
    c2.status = ChunkStatus.ACCEPTED
    c2.gate_decision = GateDecision.ACCEPT
    c2.retry_count = 1
    c2.rejection_kind = "implementation"
    c2.rejection_feedback_source = "validator-finding"
    rs.chunks = [c1, c2]

    out = tmp_path / "runs.jsonl"
    mod.append_run_summary_row(rs, 3, str(out))
    row = json.loads(out.read_text().splitlines()[0])

    assert row["test_design_retries_total"] == 2
    assert row["reject_cycles_by_chunk"] == [
        {"chunk_id": "c-rt", "executor_retry_count": 0,
         "test_design_retry_count": 2, "last_rejection_kind": "test",
         "executor_feedback_source": ""},
        {"chunk_id": "c-impl", "executor_retry_count": 1,
         "test_design_retry_count": 0, "last_rejection_kind": "implementation",
         "executor_feedback_source": "validator-finding"},
    ]
    # The executor budget's own field keeps its v3 shape.
    assert [c["retry_count"] for c in row["chunk_statuses"]] == [0, 1]


def test_test_designer_rerun_emits_its_own_phase_step(tmp_path):
    fw_root = tmp_path / "fw"
    (fw_root / "telemetry").mkdir(parents=True)
    rs = _run_state(str(tmp_path / "pilot"), framework_root=str(fw_root))
    chunk = ChunkState(chunk_id="c-rt", scope="s")
    ev = tmp_path / "ev"
    ev.mkdir()
    (ev / "prompt.md").write_text("prompt")

    per_chunk.invoke_test_designer(
        chunk,
        rs,
        evidence_output_dir=str(ev),
        rendered_prompt_path=str(ev / "prompt.md"),
        envelope_path=str(ev / "envelope.json"),
        dry_run=True,
        phase_step="test-design-rerun",
    )

    rows = [
        json.loads(line)
        for line in (fw_root / "telemetry" / "runs.jsonl").read_text().splitlines()
    ]
    assert len(rows) == 1
    assert rows[0]["role"] == "test-designer"
    assert rows[0]["phase_step"] == "test-design-rerun"


def test_orchestrate_review_summary_carries_the_finding_text():
    """The runner can only route on what the summary preserves."""
    src = open(os.path.join(_TOOLS, "orchestrate-review.py")).read()
    assert '"finding_text"' in src
    assert "REVIEW_FINDING_TEXT_LIMIT" in src
    # The verdict vocabulary the routing depends on is still parsed.
    assert "REJECT_TEST" in src
    subprocess.run(
        [sys.executable, "-m", "py_compile", os.path.join(_TOOLS, "orchestrate-review.py")],
        check=True,
    )

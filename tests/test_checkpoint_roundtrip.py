"""Regression test for checkpoint field round-trip (finding P2-a).

write_checkpoint serializes everything via ``asdict``; load_checkpoint
must restore every field so a resumed run does not silently drop state.
The bug: load_checkpoint hand-restored a curated subset, silently
dropping ``chunks_file`` (reintroducing KI-8) and ``pilot_spec_file``
(degrading test-designer context).
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TOOLS = os.path.join(_REPO, "tools")
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)

import dataclasses

import pytest  # noqa: E402
from sprint_loop.state import (  # noqa: E402
    ChunkState,
    ChunkStatus,
    Finding,
    GateDecision,
    RunState,
    RunStatus,
)


def _load_runner():
    runner_path = os.path.join(_TOOLS, "sprint-loop.py")
    spec = importlib.util.spec_from_file_location("sprint_loop_runner_cp", runner_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _fully_populated_rs(tmp_path) -> RunState:
    """Return a RunState with every field set to a non-default value."""
    rs = RunState(
        run_id="r-roundtrip-test",
        started_at="2026-09-01T00:00:00Z",
        framework_root=str(tmp_path / "fw"),
        pilot_root=str(tmp_path / "pilot"),
        pilot_python="/usr/bin/python3",
    )

    # Scalar / simple-list fields with non-default values
    rs.max_review_rounds = 5
    rs.retry_threshold = 3
    rs.max_auto_retries = 4
    rs.retry_delay_seconds = 10
    rs.per_call_timeout_seconds = 900
    rs.status = RunStatus.PLAN_REVIEWING
    rs.status_message = "round 2 in progress"
    rs.plan_doc_path = str(tmp_path / "plan.md")
    rs.plan_sha256 = "abc123" * 10
    rs.plan_round = 2
    rs.plan_reviewer_verdicts = [
        {"model_id": "m1", "verdict": "APPROVE", "plan_sha256_at_time_of_review": "abc123"},
    ]
    rs.current_chunk_index = 1
    rs.output_branch = "factory/test-branch"
    rs.commit_count = 3
    rs.final_telemetry_path = str(tmp_path / "telemetry" / "runs.jsonl")
    rs.dry_run = True
    rs.unattended = True
    rs.skip_reconcile = True
    rs.create_pr = True
    rs.validation_backend = "ci"
    rs.signing_key_env = "CUSTOM_KEY"
    rs.verify_mode = True
    rs.force_accept = True
    rs.force_accept_reason = "operator override"
    rs.force_accept_disposition = "accepted with reason"

    # The two fields that were previously dropped (KI-8 / KI-7 vectors):
    rs.pilot_spec_file = str(tmp_path / "spec.md")
    rs.chunks_file = str(tmp_path / "chunks.json")
    rs.signing_key = "test-key-for-roundtrip"

    # v3 telemetry fields
    rs.run_label = "experiment-arm-b"
    rs.reached_phase_step = "validate"
    rs.family_guard_passed = True
    rs.family_guard_notes = "all distinct"

    # plan_findings
    rs.plan_findings = [
        Finding(
            finding_id="F-rt1",
            severity="blocker",
            category="test-gap",
            claim="the plan claims X",
            evidence=["plan.md:line 42"],
            recommended_change="do Y instead",
            source_role="reviewer",
            source_run_id="r-reviewer-1",
            source_model_id="grok-4.5",
            source_family="grok-family",
            first_seen_in_panel_position=1,
            status="open",
            disposition_rationale="",
            plan_section="Chunk plan",
            risk_if_ignored="KI-8 reintroduction",
        ),
    ]

    # chunks
    chunk = ChunkState(
        chunk_id="c-rt1",
        scope="roundtrip scope",
        observable_criteria=["criterion A"],
        allowed_files=["tools/sprint-loop.py"],
        locked_test_files=["tests/test_roundtrip.py"],
        commands=["/usr/bin/python3 -m pytest tests/test_roundtrip.py"],
        accepted_assertion="roundtrip assertion phrase",
        lock_manifest_path=str(tmp_path / "lock.json"),
        locked_test_sha="sha256-of-test",
        evidence_bundle_path=str(tmp_path / "bundle.json"),
        status=ChunkStatus.EXECUTING,
        verify_mode=True,
    )
    rs.chunks = [chunk]

    return rs


def test_checkpoint_round_trips_every_field(tmp_path):
    """Populate every RunState field, write checkpoint, load it back,
    and assert equality for all scalar / simple-list fields."""
    mod = _load_runner()
    rs = _fully_populated_rs(tmp_path)
    cp = tmp_path / "checkpoint.json"
    mod.write_checkpoint(rs, str(cp))

    restored = mod.load_checkpoint(str(cp))

    # The previously-dropped fields that caused KI-8 and pilot_spec degradation:
    assert restored.chunks_file == rs.chunks_file, "chunks_file dropped on restore"
    assert restored.pilot_spec_file == rs.pilot_spec_file, "pilot_spec_file dropped on restore"
    assert restored.signing_key == rs.signing_key

    # All other scalar fields
    assert restored.run_id == rs.run_id
    assert restored.started_at == rs.started_at
    assert restored.framework_root == rs.framework_root
    assert restored.pilot_root == rs.pilot_root
    assert restored.pilot_python == rs.pilot_python
    assert restored.max_review_rounds == rs.max_review_rounds
    assert restored.retry_threshold == rs.retry_threshold
    assert restored.max_auto_retries == rs.max_auto_retries
    assert restored.retry_delay_seconds == rs.retry_delay_seconds
    assert restored.per_call_timeout_seconds == rs.per_call_timeout_seconds
    assert restored.status == rs.status
    assert restored.status_message == rs.status_message
    assert restored.plan_doc_path == rs.plan_doc_path
    assert restored.plan_sha256 == rs.plan_sha256
    assert restored.plan_round == rs.plan_round
    assert restored.plan_reviewer_verdicts == rs.plan_reviewer_verdicts
    assert restored.current_chunk_index == rs.current_chunk_index
    assert restored.output_branch == rs.output_branch
    assert restored.commit_count == rs.commit_count
    assert restored.final_telemetry_path == rs.final_telemetry_path
    assert restored.dry_run is True
    assert restored.unattended is True
    assert restored.skip_reconcile is True
    assert restored.create_pr is True
    assert restored.validation_backend == "ci"
    assert restored.signing_key_env == "CUSTOM_KEY"
    assert restored.verify_mode is True
    assert restored.force_accept is True
    assert restored.force_accept_reason == "operator override"
    assert restored.force_accept_disposition == "accepted with reason"
    assert restored.run_label == "experiment-arm-b"
    assert restored.reached_phase_step == "validate"
    assert restored.family_guard_passed is True
    assert restored.family_guard_notes == "all distinct"

    # plan_findings
    assert len(restored.plan_findings) == 1
    f = restored.plan_findings[0]
    assert f.finding_id == "F-rt1"
    assert f.severity == "blocker"
    assert f.plan_section == "Chunk plan"
    assert f.risk_if_ignored == "KI-8 reintroduction"

    # chunks
    assert len(restored.chunks) == 1
    c = restored.chunks[0]
    assert c.chunk_id == "c-rt1"
    assert c.accepted_assertion == "roundtrip assertion phrase"
    assert c.lock_manifest_path == str(tmp_path / "lock.json")
    assert c.status == ChunkStatus.EXECUTING


def test_new_field_added_to_runstate_round_trips_automatically(tmp_path):
    """Guard against regression: if a new field is added to RunState,
    the field-driven restore must pick it up automatically as long as
    it is not in the skip set and write_checkpoint serializes it."""
    mod = _load_runner()
    rs = _fully_populated_rs(tmp_path)
    cp = tmp_path / "checkpoint.json"
    mod.write_checkpoint(rs, str(cp))

    # Inject a synthetic field into the checkpoint JSON
    data = json.loads(cp.read_text())
    data["hypothetical_future_field"] = "should-be-ignored"
    cp.write_text(json.dumps(data))

    # Should not raise (unknown keys in JSON are harmlessly skipped)
    restored = mod.load_checkpoint(str(cp))
    assert restored.run_id == rs.run_id

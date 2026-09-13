"""Regression test for checkpoint field round-trip (finding P2-a / P2A blocker).

write_checkpoint serializes everything via ``asdict``; load_checkpoint
must restore every field so a resumed run does not silently drop state.

The programmatic sweep iterates dataclass fields for both RunState and
ChunkState, sets a distinct sentinel per field, writes a checkpoint,
loads it back, and asserts every non-skipped field equals its sentinel.
A future field added to either dataclass will fail this test loudly if
the restore drops it.
"""

from __future__ import annotations

import dataclasses
import importlib.util
import json
import os
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TOOLS = os.path.join(_REPO, "tools")
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)

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


# ── Sentinel factories ──────────────────────────────────────────────────
# Build a non-default sentinel for every field type we encounter.

_SENTINEL_FINDING = Finding(
    finding_id="F-sentinel",
    severity="blocker",
    category="test-gap",
    claim="sentinel claim",
    evidence=["sentinel.md:1"],
    recommended_change="fix it",
    source_role="reviewer",
    source_run_id="r-sentinel",
    source_model_id="sentinel-model",
    source_family="sentinel-family",
    first_seen_in_panel_position=7,
    status="open",
    disposition_rationale="sentinel rationale",
    plan_section="sentinel section",
    risk_if_ignored="sentinel risk",
)

# Fields that load_checkpoint intentionally skips (role assignments are
# reconstructed from Config at runtime).
_RUNSTATE_SKIP = frozenset({
    "planner", "plan_reviewer", "plan_reviewer_2",
    "test_designer", "executor", "validators",
})

# Fields that the chunk restore intentionally skips (constructor args
# handled separately; verify_mode has special OR semantics).
_CHUNKSTATE_CONSTRUCTOR = frozenset({"chunk_id", "scope"})


def _sentinel_for_field(fld: dataclasses.Field, prefix: str) -> object:
    """Return a non-default sentinel value appropriate for the field's type."""
    name = fld.name

    # Enum special cases
    if name == "status" and prefix == "rs":
        return RunStatus.PLAN_REVIEWING
    if name == "status" and prefix == "cs":
        return ChunkStatus.EXECUTING
    if name == "gate_decision":
        return GateDecision.ACCEPT_WITH_NITS

    # Nested complex types
    if name == "plan_findings":
        return [_SENTINEL_FINDING]
    if name == "findings":
        return [_SENTINEL_FINDING]
    if name == "plan_reviewer_verdicts":
        return [{"model_id": "m-sentinel", "verdict": "APPROVE",
                 "plan_sha256_at_time_of_review": "sentinel-sha"}]
    if name == "chunks":
        return "HANDLED_SEPARATELY"

    # Derive type from the default or annotation string
    default = fld.default if fld.default is not dataclasses.MISSING else None
    if fld.default_factory is not dataclasses.MISSING:
        default = fld.default_factory()

    if isinstance(default, bool) or "bool" in str(fld.type):
        return True
    if isinstance(default, int) or "int" in str(fld.type):
        return 42
    if isinstance(default, list):
        return [f"sentinel-{prefix}-{name}"]
    if isinstance(default, str) or default is None:
        return f"sentinel-{prefix}-{name}"

    # Fallback
    return f"sentinel-{prefix}-{name}"


def _fully_populated_rs(tmp_path) -> RunState:
    """Build a RunState with every field set to a non-default sentinel."""
    rs = RunState(
        run_id="r-roundtrip-sentinel",
        started_at="2026-09-01T00:00:00Z",
        framework_root=str(tmp_path / "fw"),
        pilot_root=str(tmp_path / "pilot"),
        pilot_python="/usr/bin/python3",
    )
    for fld in dataclasses.fields(RunState):
        if fld.name in _RUNSTATE_SKIP:
            continue
        if fld.name in ("run_id", "started_at", "framework_root",
                        "pilot_root", "pilot_python"):
            continue  # already set via constructor
        if fld.name == "chunks":
            continue  # handled below
        val = _sentinel_for_field(fld, "rs")
        setattr(rs, fld.name, val)
    return rs


def _fully_populated_chunk() -> ChunkState:
    """Build a ChunkState with every field set to a non-default sentinel."""
    cs = ChunkState(chunk_id="c-sentinel", scope="sentinel-scope")
    for fld in dataclasses.fields(ChunkState):
        if fld.name in _CHUNKSTATE_CONSTRUCTOR:
            continue
        val = _sentinel_for_field(fld, "cs")
        setattr(cs, fld.name, val)
    return cs


# ── Programmatic sweep ──────────────────────────────────────────────────


def test_checkpoint_round_trips_all_runstate_fields(tmp_path):
    """Every RunState field must survive write → load."""
    mod = _load_runner()
    rs = _fully_populated_rs(tmp_path)
    chunk = _fully_populated_chunk()
    # verify_mode on the chunk: set to False so the OR with rs.verify_mode
    # (True) produces True — validating the inheritance semantics.
    chunk.verify_mode = False
    rs.chunks = [chunk]

    cp = tmp_path / "checkpoint.json"
    mod.write_checkpoint(rs, str(cp))
    restored = mod.load_checkpoint(str(cp))

    # RunState field sweep
    for fld in dataclasses.fields(RunState):
        if fld.name in _RUNSTATE_SKIP:
            continue
        if fld.name == "chunks":
            continue  # checked separately below
        if fld.name == "run_label":
            # run_label falls back to run_id when empty; our sentinel is
            # non-empty so it should round-trip.
            pass
        original = getattr(rs, fld.name)
        restored_val = getattr(restored, fld.name)
        assert restored_val == original, (
            f"RunState.{fld.name} dropped on restore: "
            f"expected {original!r}, got {restored_val!r}"
        )


def test_checkpoint_round_trips_all_chunkstate_fields(tmp_path):
    """Every ChunkState field must survive write → load."""
    mod = _load_runner()
    rs = _fully_populated_rs(tmp_path)
    chunk = _fully_populated_chunk()
    # verify_mode inheritance: chunk=False, rs=True → restored chunk=True
    chunk.verify_mode = False
    rs.chunks = [chunk]

    cp = tmp_path / "checkpoint.json"
    mod.write_checkpoint(rs, str(cp))
    restored = mod.load_checkpoint(str(cp))

    assert len(restored.chunks) == 1
    rc = restored.chunks[0]

    for fld in dataclasses.fields(ChunkState):
        original = getattr(chunk, fld.name)
        restored_val = getattr(rc, fld.name)
        if fld.name == "verify_mode":
            # verify_mode inherits from rs: chunk was False, rs was True,
            # so the restored value is True (deliberate OR).
            assert restored_val is True, (
                "verify_mode OR inheritance broken: chunk=False, rs=True "
                f"→ expected True, got {restored_val!r}"
            )
            continue
        if fld.name == "findings":
            # Compare finding_ids; Finding objects don't have __eq__
            assert len(restored_val) == len(original), (
                f"ChunkState.findings count mismatch: "
                f"{len(restored_val)} != {len(original)}"
            )
            for rf, of in zip(restored_val, original):
                assert rf.finding_id == of.finding_id
                assert rf.severity == of.severity
                assert rf.risk_if_ignored == of.risk_if_ignored
            continue
        assert restored_val == original, (
            f"ChunkState.{fld.name} dropped on restore: "
            f"expected {original!r}, got {restored_val!r}"
        )


def test_checkpoint_preserves_executor_retry_count_and_rejection_feedback(tmp_path):
    """Resume keeps the retry budget spent and the finding for the next seat."""
    mod = _load_runner()
    rs = RunState(
        run_id="r-retry-feedback",
        started_at="2026-09-13T00:00:00Z",
        framework_root=str(tmp_path / "fw"),
        pilot_root=str(tmp_path / "pilot"),
        pilot_python="/usr/bin/python3",
    )
    chunk = ChunkState(chunk_id="c-retry-feedback", scope="fix the rejected behavior")
    chunk.retry_count = 1
    chunk.rejection_feedback = [
        "validator-a: the implementation substitutes a fallback instead of "
        "reporting the deleted reference"
    ]
    rs.chunks = [chunk]

    cp = tmp_path / "checkpoint.json"
    mod.write_checkpoint(rs, str(cp))
    restored = mod.load_checkpoint(str(cp)).chunks[0]

    assert restored.retry_count == 1
    assert restored.rejection_feedback == chunk.rejection_feedback


def test_verify_mode_or_inheritance(tmp_path):
    """verify_mode on a chunk must OR with the run-level flag."""
    mod = _load_runner()
    rs = _fully_populated_rs(tmp_path)
    rs.verify_mode = True

    chunk = _fully_populated_chunk()
    chunk.verify_mode = False
    rs.chunks = [chunk]

    cp = tmp_path / "checkpoint.json"
    mod.write_checkpoint(rs, str(cp))
    restored = mod.load_checkpoint(str(cp))

    # chunk=False OR rs=True → True
    assert restored.chunks[0].verify_mode is True


def test_gate_decision_none_round_trips(tmp_path):
    """gate_decision=None must survive checkpoint (not crash on enum)."""
    mod = _load_runner()
    rs = _fully_populated_rs(tmp_path)
    chunk = _fully_populated_chunk()
    chunk.gate_decision = None
    rs.chunks = [chunk]

    cp = tmp_path / "checkpoint.json"
    mod.write_checkpoint(rs, str(cp))
    restored = mod.load_checkpoint(str(cp))

    assert restored.chunks[0].gate_decision is None


def test_unknown_json_keys_are_harmlessly_skipped(tmp_path):
    """Extra keys in checkpoint JSON must not crash load_checkpoint."""
    mod = _load_runner()
    rs = _fully_populated_rs(tmp_path)
    rs.chunks = [_fully_populated_chunk()]
    cp = tmp_path / "checkpoint.json"
    mod.write_checkpoint(rs, str(cp))

    data = json.loads(cp.read_text())
    data["hypothetical_future_field"] = "should-be-ignored"
    data["chunks"][0]["hypothetical_chunk_field"] = "also-ignored"
    cp.write_text(json.dumps(data))

    restored = mod.load_checkpoint(str(cp))
    assert restored.run_id == rs.run_id
    assert restored.chunks[0].chunk_id == "c-sentinel"

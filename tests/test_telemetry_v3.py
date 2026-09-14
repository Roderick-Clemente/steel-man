"""Tests for the SCHEMA.md v3 telemetry surface.

Covers the pieces that turn per-call rows into a queryable funnel:
run provenance, the ``role="run"`` summary row, force-accept
disposition rows, the aggregator's multi-version schema check, and
the flattened provenance on ``RunRecord.to_telemetry_row``.

Pure-data plus a subprocess call to ``telemetry/aggregate.py``. No
droid, no writes outside tmp_path.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TOOLS = os.path.join(_REPO, "tools")
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)

import pytest  # noqa: E402
from sprint_loop.droid import RunRecord  # noqa: E402
from sprint_loop.provenance import run_provenance  # noqa: E402
from sprint_loop.state import (  # noqa: E402
    ChunkState,
    ChunkStatus,
    Finding,
    GateDecision,
    RunState,
    RunStatus,
)

PROVENANCE_KEYS = {
    "run_label",
    "framework_sha",
    "framework_branch",
    "pilot_root",
    "pilot_head",
    "plan_sha256",
    "plan_round",
    "flag_unattended",
    "flag_force_accept",
    "flag_verify_mode",
    "flag_dry_run",
    "flag_skip_reconcile",
}


def _load_sprint_loop_module():
    """Load sprint-loop.py as a module without running main()."""
    import importlib.util

    runner_path = os.path.join(_REPO, "tools", "sprint-loop.py")
    spec = importlib.util.spec_from_file_location("sprint_loop_runner_v3", runner_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _schema_md() -> str:
    return open(os.path.join(_REPO, "telemetry", "SCHEMA.md")).read()


def _schema_enum_members(field_name: str) -> list[str]:
    schema = _schema_md()
    match = re.search(rf"\| `{re.escape(field_name)}`\s+\| enum\s+\| ([^\n|]+) \|", schema)
    assert match, f"{field_name} enum row missing from SCHEMA.md"
    return re.findall(r"`([^`]+)`", match.group(1))


def _make_rs(tmp_path, **overrides) -> RunState:
    kwargs = dict(
        run_id="r-phase45-test",
        started_at="2026-01-01T00:00:00Z",
        framework_root=_REPO,
        pilot_root=str(tmp_path),
        pilot_python=sys.executable,
        run_label="arm-a",
        unattended=True,
        force_accept=True,
        dry_run=True,
    )
    kwargs.update(overrides)
    rs = RunState(**kwargs)
    rs.plan_sha256 = "abc123"
    rs.plan_round = 2
    return rs


def _finding(i: int, severity: str = "blocker") -> Finding:
    return Finding(
        finding_id=f"F-{i:03d}",
        severity=severity,
        category="correctness",
        claim=f"claim {i}",
        evidence=[f"file.py:{i}"],
        recommended_change="fix it",
        source_role="reviewer",
        source_run_id=f"r-rev-{i}",
        source_model_id="model-x",
        source_family="x-family",
    )


# ── (a) run_provenance ───────────────────────────────────────────────────


def test_run_provenance_returns_all_expected_keys(tmp_path):
    rs = _make_rs(tmp_path, skip_reconcile=True, verify_mode=True)
    prov = run_provenance(rs)

    assert set(prov.keys()) == PROVENANCE_KEYS
    assert prov["run_label"] == "arm-a"
    assert prov["pilot_root"] == str(tmp_path)
    assert prov["plan_sha256"] == "abc123"
    assert prov["plan_round"] == 2
    assert prov["flag_unattended"] is True
    assert prov["flag_force_accept"] is True
    assert prov["flag_verify_mode"] is True
    assert prov["flag_dry_run"] is True
    assert prov["flag_skip_reconcile"] is True
    # framework_root is a real git checkout; the pilot tmp dir is not.
    assert prov["framework_sha"] != "unknown"
    assert prov["framework_branch"] not in ("", "unknown")
    assert prov["pilot_head"] == "unknown"


def test_run_provenance_flags_are_bool_not_truthy(tmp_path):
    rs = _make_rs(tmp_path, unattended=False, force_accept=False, dry_run=False)
    prov = run_provenance(rs)
    for k in (
        "flag_unattended",
        "flag_force_accept",
        "flag_verify_mode",
        "flag_dry_run",
        "flag_skip_reconcile",
    ):
        assert isinstance(prov[k], bool), k
        assert prov[k] is False, k


# ── (b) append_run_summary_row ───────────────────────────────────────────


def test_append_run_summary_row_writes_one_v3_run_row(tmp_path):
    mod = _load_sprint_loop_module()
    rs = _make_rs(tmp_path)
    rs.status = RunStatus.COMPLETED
    rs.status_message = "done"
    rs.reached_phase_step = "completed"
    rs.plan_findings = [_finding(1, "blocker"), _finding(2, "low"), _finding(3, "blocker")]
    rs.plan_reviewer_verdicts = [
        {"model_id": "m1", "verdict": "APPROVE", "plan_sha256_at_time_of_review": "abc123"},
        {"model_id": "m2", "verdict": "REJECT", "plan_sha256_at_time_of_review": "stale"},
    ]
    cs = ChunkState(chunk_id="chunk-1", scope="s")
    cs.status = ChunkStatus.ACCEPTED
    cs.gate_decision = GateDecision.ACCEPT
    cs.retry_count = 1
    rs.chunks = [cs]

    out = tmp_path / "tele" / "runs.jsonl"
    mod.append_run_summary_row(rs, 0, str(out))

    lines = out.read_text().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])

    assert row["schema_version"] == "v3"
    assert row["role"] == "run"
    assert row["run_id"].startswith("r-run-")
    assert row["phase"] == "phase-4.5"
    assert row["exit_code"] == 0
    assert row["run_status"] == "COMPLETED"
    assert row["status_message"] == "done"
    assert row["reached_phase_step"] == "completed"
    assert row["findings_total"] == 3
    assert row["findings_by_severity"] == {"blocker": 2, "low": 1}
    assert row["plan_reviewer_verdicts"] == [
        {"model_id": "m1", "verdict": "APPROVE", "bound_to_plan": True},
        {"model_id": "m2", "verdict": "REJECT", "bound_to_plan": False},
    ]
    assert row["chunk_statuses"] == [
        {"chunk_id": "chunk-1", "status": "ACCEPTED", "gate_decision": "ACCEPT", "retry_count": 1}
    ]
    assert row["branch"] == row["framework_branch"]
    for k in PROVENANCE_KEYS:
        assert k in row, k
    assert row["run_label"] == "arm-a"


def test_append_run_summary_row_nonzero_exit_and_empty_state(tmp_path):
    mod = _load_sprint_loop_module()
    rs = _make_rs(tmp_path)
    out = tmp_path / "runs.jsonl"
    mod.append_run_summary_row(rs, 5, str(out))
    row = json.loads(out.read_text().splitlines()[0])
    assert row["exit_code"] == 5
    assert row["reached_phase_step"] == "start"
    assert row["findings_total"] == 0
    assert row["chunk_statuses"] == []


# ── (c) _append_disposition_rows ─────────────────────────────────────────


def test_append_disposition_rows_writes_one_overridden_row_per_finding(tmp_path):
    mod = _load_sprint_loop_module()
    rs = _make_rs(tmp_path)
    findings = [_finding(1), _finding(2, "high"), _finding(3)]
    out = tmp_path / "dispositions.jsonl"

    mod._append_disposition_rows(rs, findings, "overridden", "ship it", str(out))

    rows = [json.loads(line) for line in out.read_text().splitlines()]
    assert len(rows) == 3
    assert [r["finding_id"] for r in rows] == ["F-001", "F-002", "F-003"]
    for r in rows:
        assert r["schema_version"] == "v3"
        assert r["disposition"] == "overridden"
        assert r["disposition_reason"] == "ship it"
        assert r["disposition_model_id"] == "(operator)"
        assert r["phase"] == "phase-4.5"
        assert r["run_label"] == "arm-a"
        assert r["plan_sha256"] == "abc123"
        assert "framework_sha" in r
        assert "disposition_at" in r
    assert rows[1]["severity"] == "high"
    assert rows[1]["source_run_id"] == "r-rev-2"


def test_append_disposition_rows_noop_on_empty(tmp_path):
    mod = _load_sprint_loop_module()
    rs = _make_rs(tmp_path)
    out = tmp_path / "dispositions.jsonl"
    mod._append_disposition_rows(rs, [], "overridden", "x", str(out))
    assert not out.exists()


# ── (d) aggregate.py --schema-check accepts v1/v2/v3 ─────────────────────


def _base_row(version: str) -> dict:
    return {
        "schema_version": version,
        "ts": "2026-01-01T00:00:00Z",
        "run_id": f"r-{version}",
        "phase": "phase-4.5",
        "branch": "b",
        "role": "planner",
        "model_id": "m",
        "provider": "p",
        "family": "f",
        "input_tokens": 1,
        "output_tokens": 1,
    }


def _run_schema_check(data_dir) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, os.path.join(_REPO, "telemetry", "aggregate.py"),
         "--data-dir", str(data_dir), "--schema-check"],
        capture_output=True, text=True, timeout=60, check=False,
    )


def test_aggregate_schema_check_accepts_v1_v2_v3(tmp_path):
    runs = tmp_path / "runs.jsonl"
    runs.write_text("".join(json.dumps(_base_row(v)) + "\n" for v in ("v1", "v2", "v3")))
    r = _run_schema_check(tmp_path)
    assert r.returncode == 0, r.stderr + r.stdout
    assert "ok on all rows" in r.stdout


def test_aggregate_schema_check_rejects_unknown_version(tmp_path):
    runs = tmp_path / "runs.jsonl"
    runs.write_text(json.dumps(_base_row("v3")) + "\n" + json.dumps(_base_row("v9")) + "\n")
    r = _run_schema_check(tmp_path)
    assert r.returncode == 1
    assert "1 rows have schema_version" in r.stderr


def test_schema_front_matter_declares_v3_rows():
    schema = _schema_md()
    assert (
        '| `schema_version` | string | yes | `"v3"` for rows written by the Phase 4.5 runner; '
        '`"v2"` for older Phase 3.2+ rows; `"v1"` for legacy rows. |'
    ) in schema


def test_schema_disposition_enum_documents_overridden():
    schema = _schema_md()
    assert (
        '| `disposition`             | enum     | yes | `fixed` / `wontfix-with-reason` '
        '/ `deferred` / `wontfix` / `reverted` / `overridden` |'
    ) in schema


def test_schema_phase_step_enum_matches_current_emitters():
    assert _schema_enum_members("phase_step") == [
        "plan",
        "plan-review",
        "test-design",
        "execute",
    ]


def test_schema_reached_phase_step_enum_matches_current_emitters():
    assert _schema_enum_members("reached_phase_step") == [
        "start",
        "planner",
        "plan-review",
        "reconcile",
        "chunking",
        "chunk-execution",
        "test-design",
        "red-gate",
        "execute",
        "verify-green",
        "validate",
        "completed",
    ]


# ── (e) RunRecord.to_telemetry_row v3 shape ──────────────────────────────


def test_run_record_to_telemetry_row_includes_provenance_and_seat_outcome(tmp_path):
    rs = _make_rs(tmp_path)
    prov = run_provenance(rs)
    rr = RunRecord(
        run_id="r-x",
        role="executor",
        model_id="m",
        provider="p",
        family="f",
        provider_lock="p",
        api_provider_lock="p",
        seat_outcome="dry-run",
        run_label=rs.run_label,
        chunk_id="chunk-7",
        phase_step="execute",
        provenance=prov,
    )
    row = rr.to_telemetry_row(phase="phase-4.5", branch="the-branch")

    assert row["schema_version"] == "v3"
    assert row["branch"] == "the-branch"
    assert row["seat_outcome"] == "dry-run"
    assert row["chunk_id"] == "chunk-7"
    assert row["phase_step"] == "execute"
    assert row["run_label"] == "arm-a"
    for k in PROVENANCE_KEYS:
        assert k in row, k
    assert row["framework_sha"] == prov["framework_sha"]
    assert row["flag_dry_run"] is True
    # v3 artifact-state keys are always present, even when empty.
    for k in ("stderr_path", "envelope_raw_bytes", "started_at", "finished_at"):
        assert k in row, k
    # Empty optional funnel keys are omitted, not emitted as "".
    assert "verdict_text_first_240" not in row
    assert "note" not in row


def test_run_record_to_telemetry_row_defaults_seat_outcome_ok():
    rr = RunRecord(
        run_id="r-y", role="planner", model_id="m", provider="p", family="f",
        provider_lock="p", api_provider_lock="p",
    )
    row = rr.to_telemetry_row(phase="phase-4.5", branch="b")
    assert row["seat_outcome"] == "ok"
    assert "chunk_id" not in row
    assert "framework_sha" not in row


# ── per-chunk seats emit rows ────────────────────────────────────────────


@pytest.mark.parametrize(
    "invoke_name,expected_role,expected_step",
    [
        ("invoke_test_designer", "test-designer", "test-design"),
        ("invoke_executor", "executor", "execute"),
    ],
)
def test_per_chunk_seats_emit_v3_rows_in_dry_run(
    tmp_path, invoke_name, expected_role, expected_step
):
    """Before v3 neither per-chunk seat wrote a runs.jsonl row."""
    from sprint_loop import per_chunk

    fw_root = tmp_path / "fw"
    (fw_root / "telemetry").mkdir(parents=True)
    rs = _make_rs(tmp_path / "pilot", framework_root=str(fw_root), run_label="arm-d")
    chunk = ChunkState(chunk_id="chunk-9", scope="s")
    ev = tmp_path / "ev"
    ev.mkdir()
    prompt = ev / "prompt.md"
    prompt.write_text("prompt")

    getattr(per_chunk, invoke_name)(
        chunk,
        rs,
        evidence_output_dir=str(ev),
        rendered_prompt_path=str(prompt),
        envelope_path=str(ev / "envelope.json"),
        dry_run=True,
    )

    rows = [
        json.loads(line)
        for line in (fw_root / "telemetry" / "runs.jsonl").read_text().splitlines()
    ]
    assert len(rows) == 1
    row = rows[0]
    assert row["schema_version"] == "v3"
    assert row["role"] == expected_role
    assert row["phase_step"] == expected_step
    assert row["chunk_id"] == "chunk-9"
    assert row["run_label"] == "arm-d"
    assert row["seat_outcome"] == "dry-run"
    assert row["phase"] == "phase-4.5"
    assert row["branch"] == row["framework_branch"]
    assert "framework_sha" in row
    assert row["flag_dry_run"] is True


# ── runner wiring: --run-label + checkpoint round-trip ───────────────────


def test_runner_argparser_has_run_label_flag():
    mod = _load_sprint_loop_module()
    ns, _ = mod._runner_argparser().parse_known_args(["--run-label", "arm-b"])
    assert ns.run_label == "arm-b"
    ns, _ = mod._runner_argparser().parse_known_args([])
    assert ns.run_label == ""


def test_checkpoint_round_trips_v3_run_state_fields(tmp_path):
    mod = _load_sprint_loop_module()
    rs = _make_rs(tmp_path, run_label="arm-c", unattended=True)
    rs.reached_phase_step = "red-gate"
    cp = tmp_path / "checkpoint.json"
    mod.write_checkpoint(rs, str(cp))

    restored = mod.load_checkpoint(str(cp))
    assert restored.run_label == "arm-c"
    assert restored.unattended is True
    assert restored.reached_phase_step == "red-gate"


def test_checkpoint_load_defaults_v3_fields_when_absent(tmp_path):
    mod = _load_sprint_loop_module()
    rs = _make_rs(tmp_path)
    cp = tmp_path / "checkpoint.json"
    data = json.loads(rs.to_json())
    for k in ("run_label", "unattended", "reached_phase_step"):
        data.pop(k, None)
    cp.write_text(json.dumps(data))

    restored = mod.load_checkpoint(str(cp))
    assert restored.run_label == rs.run_id
    assert restored.unattended is False
    assert restored.reached_phase_step == "start"


def test_main_wrapper_emits_run_row_on_system_exit(tmp_path, monkeypatch):
    """A refusal must still leave a ``role="run"`` row, else the funnel
    cannot see where runs die."""
    mod = _load_sprint_loop_module()
    fw_root = tmp_path / "fw"
    (fw_root / "telemetry").mkdir(parents=True)
    rs = _make_rs(tmp_path, framework_root=str(fw_root), run_label="arm-e")
    rs.reached_phase_step = "reconcile"

    def fake_inner(argv):
        mod._CURRENT_RUN_STATE = rs
        raise SystemExit(4)

    monkeypatch.setattr(mod, "_main_inner", fake_inner)
    with pytest.raises(SystemExit) as ei:
        mod.main([])
    assert ei.value.code == 4

    rows = [
        json.loads(line)
        for line in (fw_root / "telemetry" / "runs.jsonl").read_text().splitlines()
    ]
    assert len(rows) == 1
    assert rows[0]["role"] == "run"
    assert rows[0]["exit_code"] == 4
    assert rows[0]["reached_phase_step"] == "reconcile"
    assert rows[0]["run_label"] == "arm-e"


def test_main_wrapper_skips_run_row_when_no_run_state(tmp_path, monkeypatch):
    mod = _load_sprint_loop_module()

    def fake_inner(argv):
        raise SystemExit(2)

    monkeypatch.setattr(mod, "_main_inner", fake_inner)
    monkeypatch.setattr(
        mod, "append_run_summary_row",
        lambda *a, **k: pytest.fail("summary row must not be written without a RunState"),
    )
    with pytest.raises(SystemExit):
        mod.main([])
    assert mod._CURRENT_RUN_STATE is None


@pytest.mark.parametrize(
    "argv,expected_peer",
    [
        (["--dry-run", "--run-label", "x", "--config", "c"], ["--dry-run", "--config", "c"]),
        (["--run-label=x", "--config", "c"], ["--config", "c"]),
        (["--resume-from", "p", "--run-label", "x"], []),
    ],
)
def test_main_strips_run_label_from_peer_argv(monkeypatch, argv, expected_peer):
    """``build_config`` has its own strict parser; the runner-only
    ``--run-label`` must not leak into it."""
    mod = _load_sprint_loop_module()
    captured: dict = {}

    def fake_build_config(peer_argv):
        captured["peer"] = list(peer_argv)
        raise SystemExit(99)

    monkeypatch.setattr(mod, "build_config", fake_build_config)
    with pytest.raises(SystemExit) as ei:
        mod._main_inner(argv)
    assert ei.value.code == 99
    assert captured["peer"] == expected_peer


# ── §7 uncommitted-tree guard scoping ───────────────────────────────────


def _guard_fixture(tmp_path, monkeypatch, dirty: bool):
    """Load the runner and point its repo-root git calls at a fake status."""
    mod = _load_sprint_loop_module()
    monkeypatch.setattr(
        mod, "_git", lambda *a, **k: " M tools/sprint-loop.py\n" if dirty else ""
    )
    return mod


def test_guard_refuses_when_evidence_is_inside_framework_root(tmp_path, monkeypatch):
    mod = _guard_fixture(tmp_path, monkeypatch, dirty=True)
    inside = os.path.join(mod._REPO_ROOT, "evidence", "phase-4.5", "build-evidence", "r-x")
    with pytest.raises(SystemExit) as exc:
        mod.guard_in_uncommitted_state(inside)
    assert "uncommitted changes" in str(exc.value)


def test_guard_proceeds_when_evidence_is_outside_framework_root(
    tmp_path, monkeypatch, capsys
):
    """An overlay layout stages nothing here, so the hazard cannot occur."""
    mod = _guard_fixture(tmp_path, monkeypatch, dirty=True)
    mod.guard_in_uncommitted_state(str(tmp_path / "build-evidence" / "r-x"))
    assert "evidence tree is outside it" in capsys.readouterr().err


def test_guard_is_silent_on_a_clean_tree(tmp_path, monkeypatch, capsys):
    mod = _guard_fixture(tmp_path, monkeypatch, dirty=False)
    mod.guard_in_uncommitted_state(str(tmp_path))
    assert capsys.readouterr().err == ""


def test_guard_without_an_evidence_dir_still_refuses_a_dirty_tree(monkeypatch):
    """No evidence dir means no proof the audit commit is a no-op."""
    mod = _guard_fixture(None, monkeypatch, dirty=True)
    with pytest.raises(SystemExit):
        mod.guard_in_uncommitted_state()

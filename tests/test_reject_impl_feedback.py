"""KI-16: the executor retry must carry the rejecting validator's finding.

The test-designer was given ``{{prior_test_rejection}}`` when REJECT_TEST
routing was added; the executor had the same defect unfixed — a
REJECT_IMPLEMENTATION retry re-ran the most expensive seat in the pipeline
with no knowledge of why the previous attempt was refused. These tests pin
the fix: the rejecting seats' own finding text reaches the executor's
rendered prompt, the accepting seats' does not, multiple rejecting seats
are attributed and ordered, a first attempt carries no prior-rejection
section, a REJECT_TEST cycle does not double-feed the executor, and the
telemetry distinguishes a finding-carrying retry from a gate-reason-only one.
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

from conftest import (  # noqa: E402
    _load_runner_module,
    _observed,
    _run_state,
    _stub_loop,
)
from sprint_loop import per_chunk as per_chunk_module  # noqa: E402
from sprint_loop.backends import BackendResult  # noqa: E402
from sprint_loop.config import Config  # noqa: E402
from sprint_loop.droid import RunRecord  # noqa: E402
from sprint_loop.per_chunk import (  # noqa: E402
    FEEDBACK_SOURCE_GATE_REASON,
    FEEDBACK_SOURCE_VALIDATOR_FINDING,
    format_implementation_rejection_feedback,
    implementation_rejection_has_finding,
    render_executor_prompt,
)
from sprint_loop.state import (  # noqa: E402
    ChunkState,
    ChunkStatus,
    GateDecision,
    Role,
)


def _chunk() -> ChunkState:
    return ChunkState(
        chunk_id="c-ri",
        scope="report a stored reference to a deleted entity as such",
        observable_criteria=["a deleted-entity reference is reported, not substituted"],
        locked_test_files=["test/test_devices.py"],
        commands=["/usr/bin/true -m pytest test/test_devices.py -v"],
        accepted_assertion="deleted reference reported",
    )


_FINDING_A = (
    "The criterion requires that a stored reference to a deleted entity be "
    "reported as such. The implementation silently substitutes a fallback "
    "instead, so the criterion is never met."
)

_FINDING_B = (
    "The docstring rewrites the criterion into a weaker one. The observable "
    "test expects an error, not a fallback value."
)


def _reject_impl_one_rejects() -> BackendResult:
    """One seat rejects the implementation, one accepts."""
    return BackendResult(
        gate=GateDecision.REJECT,
        reason="1 validator(s) returned REJECT",
        validators=[
            {
                "label": "grok-4.5",
                "model": "grok-4.5",
                "family": "grok-family",
                "verdict": "REJECT_IMPLEMENTATION",
                "finding_text": _FINDING_A,
                "envelope_path": "/tmp/reviews/review-grok-4.5-envelope.json",
            },
            {
                "label": "gemini-3.1-pro-preview",
                "model": "gemini-3.1-pro-preview",
                "family": "gemini-family",
                "verdict": "ACCEPT",
                "finding_text": "The implementation looks correct.",
                "envelope_path": "/tmp/reviews/review-gemini-envelope.json",
            },
        ],
    )


def _reject_impl_two_reject() -> BackendResult:
    """Two seats reject the implementation."""
    return BackendResult(
        gate=GateDecision.REJECT,
        reason="2 validator(s) returned REJECT",
        validators=[
            {
                "label": "grok-4.5",
                "model": "grok-4.5",
                "family": "grok-family",
                "verdict": "REJECT_IMPLEMENTATION",
                "finding_text": _FINDING_A,
                "envelope_path": "/tmp/reviews/review-grok-4.5-envelope.json",
            },
            {
                "label": "gemini-3.1-pro-preview",
                "model": "gemini-3.1-pro-preview",
                "family": "gemini-family",
                "verdict": "REJECT",
                "finding_text": _FINDING_B,
                "envelope_path": "/tmp/reviews/review-gemini-envelope.json",
            },
        ],
    )


def _reject_test_result() -> BackendResult:
    """A test-directed rejection — must route to the test-designer."""
    return BackendResult(
        gate=GateDecision.REJECT,
        reason="1 validator(s) returned REJECT",
        validators=[
            {
                "label": "grok-4.5",
                "model": "grok-4.5",
                "family": "grok-family",
                "verdict": "REJECT_TEST",
                "finding_text": _FINDING_A,
                "envelope_path": "/tmp/reviews/review-grok-4.5-envelope.json",
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


# ── the formatter ────────────────────────────────────────────────────────


def test_format_impl_rejection_feedback_carries_the_rejecting_seats_reasoning():
    text = format_implementation_rejection_feedback(_reject_impl_one_rejects())
    assert _FINDING_A in text
    assert "REJECT_IMPLEMENTATION" in text
    assert "grok-4.5" in text
    # The ACCEPTing seat's prose is not an implementation finding.
    assert "gemini-3.1-pro-preview" not in text
    assert "The implementation looks correct." not in text


def test_format_impl_rejection_feedback_excludes_test_directed_verdicts():
    """A REJECT_TEST finding must not appear in the executor's feedback."""
    text = format_implementation_rejection_feedback(_reject_test_result())
    assert _FINDING_A not in text
    assert "REJECT_TEST" not in text


def test_format_impl_rejection_feedback_falls_back_to_gate_reason():
    res = BackendResult(
        gate=GateDecision.REJECT,
        reason="dry-run: simulated REJECT_IMPLEMENTATION",
        validators=[{"label": "v1", "verdict": "REJECT_IMPLEMENTATION"}],
    )
    assert format_implementation_rejection_feedback(res) == "dry-run: simulated REJECT_IMPLEMENTATION"


def test_implementation_rejection_has_finding_detects_real_findings():
    assert implementation_rejection_has_finding(_reject_impl_one_rejects()) is True
    assert implementation_rejection_has_finding(_reject_test_result()) is False
    no_finding = BackendResult(
        gate=GateDecision.REJECT,
        reason="dry-run",
        validators=[{"label": "v1", "verdict": "REJECT_IMPLEMENTATION"}],
    )
    assert implementation_rejection_has_finding(no_finding) is False


# ── the rendered prompt ──────────────────────────────────────────────────


def test_executor_prompt_contains_rejecting_finding_on_retry(tmp_path):
    """On a REJECT_IMPLEMENTATION retry, the executor's rendered prompt
    carries the rejecting validator's finding text."""
    rs = _run_state(str(tmp_path / "pilot"))
    chunk = _chunk()
    chunk.rejection_feedback = [format_implementation_rejection_feedback(
        _reject_impl_one_rejects()
    )]
    out = tmp_path / "ex-prompt.md"
    render_executor_prompt(chunk, rs, output_path=str(out))
    text = out.read_text()

    assert _FINDING_A in text
    assert "Prior rejection feedback" in text
    assert "{{" not in text


def test_accepting_validator_text_not_in_executor_prompt(tmp_path):
    """When one seat accepts and one rejects, the accepting seat's prose
    is NOT in the executor's prompt."""
    rs = _run_state(str(tmp_path / "pilot"))
    chunk = _chunk()
    chunk.rejection_feedback = [format_implementation_rejection_feedback(
        _reject_impl_one_rejects()
    )]
    out = tmp_path / "ex-prompt.md"
    render_executor_prompt(chunk, rs, output_path=str(out))
    text = out.read_text()

    assert _FINDING_A in text
    assert "The implementation looks correct." not in text
    assert "gemini-3.1-pro-preview" not in text


def test_two_rejecting_seats_both_appear_attributed_stable_order(tmp_path):
    """When more than one seat rejects, each finding appears attributed
    to its model id, in the panel order the backend reports."""
    rs = _run_state(str(tmp_path / "pilot"))
    chunk = _chunk()
    chunk.rejection_feedback = [format_implementation_rejection_feedback(
        _reject_impl_two_reject()
    )]
    out = tmp_path / "ex-prompt.md"
    render_executor_prompt(chunk, rs, output_path=str(out))
    text = out.read_text()

    assert _FINDING_A in text
    assert _FINDING_B in text
    assert "grok-4.5" in text
    assert "gemini-3.1-pro-preview" in text
    # Stable order: grok appears before gemini (panel order).
    assert text.index("grok-4.5") < text.index("gemini-3.1-pro-preview")
    assert "{{" not in text


def test_first_attempt_no_prior_rejection_section_no_placeholders(tmp_path):
    """A first attempt (empty rejection_feedback) renders no prior-rejection
    section and leaves no {{ anywhere in the prompt."""
    rs = _run_state(str(tmp_path / "pilot"))
    chunk = _chunk()
    # rejection_feedback is empty by default — first attempt.
    out = tmp_path / "ex-prompt.md"
    render_executor_prompt(chunk, rs, output_path=str(out))
    text = out.read_text()

    assert "Prior rejection feedback" not in text
    assert _FINDING_A not in text
    assert "{{" not in text


def test_executor_prompt_with_placeholder_in_finding_text_does_not_leak(tmp_path):
    """A validator that quotes {{...}} in its finding must not plant a live
    placeholder in the executor's prompt."""
    rs = _run_state(str(tmp_path / "pilot"))
    chunk = _chunk()
    res = BackendResult(
        gate=GateDecision.REJECT,
        reason="1 REJECT",
        validators=[
            {
                "label": "grok-4.5",
                "model": "grok-4.5",
                "family": "grok-family",
                "verdict": "REJECT_IMPLEMENTATION",
                "finding_text": "The {{chunk_spec}} was not met.",
            },
        ],
    )
    chunk.rejection_feedback = [format_implementation_rejection_feedback(res)]
    out = tmp_path / "ex-prompt.md"
    render_executor_prompt(chunk, rs, output_path=str(out))
    text = out.read_text()

    assert "{{" not in text
    assert "chunk_spec" in text  # the defused text is still present


# ── end-to-end through the retry loop ─────────────────────────────────────


def test_reject_impl_retry_renders_finding_into_executor_prompt(tmp_path, monkeypatch):
    """End-to-end: after a REJECT_IMPLEMENTATION, the re-fired executor's
    prompt file carries the rejecting validator's finding."""
    mod = _load_runner_module()
    pilot = tmp_path / "pilot"
    (pilot / "test").mkdir(parents=True)
    (pilot / "test" / "test_devices.py").write_text("def test_devices():\n    assert True\n")
    rs = _run_state(str(pilot))
    chunk = _chunk()
    observed = _observed()
    _stub_loop(mod, monkeypatch, chunk, tmp_path, observed)
    results = [_reject_impl_one_rejects(), _accept_result()]
    monkeypatch.setattr(mod, "run_validators", lambda *a, **k: results.pop(0))

    ev = tmp_path / "ev"
    chunk = mod.run_chunk_with_retries(rs, chunk, str(ev), False, Config())

    assert chunk.status == ChunkStatus.ACCEPTED
    assert chunk.retry_count == 1
    prompt = (ev / "c-ri-ex-prompt.md").read_text()
    assert _FINDING_A in prompt
    assert "The implementation looks correct." not in prompt
    assert "{{" not in prompt


def test_live_reject_impl_retry_crosses_real_red_gate_with_finding(
    tmp_path, monkeypatch
):
    """A live retry starts from the GREEN implementation just rejected.

    Only the droid-backed executor and validator seats are replaced. Locking,
    validate-red, verify-green, evidence production, prompt rendering, and
    the retry controller all run through their real subprocess-backed paths.
    """
    mod = _load_runner_module("sprint_loop_runner_live_reject_impl")
    pilot = tmp_path / "pilot"
    pilot.mkdir()
    (pilot / "app.py").write_text('def value():\n    return "not-fixed"\n')
    (pilot / "test_feature.py").write_text(
        "from app import value\n\n"
        "def test_value():\n"
        '    assert value() == "fixed", "implementation returns fixed"\n'
    )
    subprocess.run(["git", "init", "-q"], cwd=pilot, check=True)
    subprocess.run(["git", "add", "."], cwd=pilot, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-qm",
            "baseline",
        ],
        cwd=pilot,
        check=True,
    )

    # Keep every generated artifact under tmp_path while using the real
    # framework scripts through symlinks.
    framework = tmp_path / "framework"
    (framework / "tools").mkdir(parents=True)
    (framework / "telemetry").mkdir()
    os.symlink(
        os.path.join(_TOOLS, "phase-1-scripts"),
        framework / "tools" / "phase-1-scripts",
    )
    evidence_code = framework / "tools" / "phase-3.2-evidence"
    evidence_code.mkdir()
    producer_source = open(
        os.path.join(_TOOLS, "phase-3.2-evidence", "local_backend.py")
    ).read()
    # The repository's mandated test interpreter is Python 3.9, while this
    # standalone producer intentionally retains a PEP-604 annotation pinned
    # by the layout tests. Defer annotation evaluation in the temporary copy
    # so this test can exercise the producer logic rather than that known
    # interpreter compatibility boundary.
    producer_source = producer_source.replace(
        "\nimport argparse\n",
        "\nfrom __future__ import annotations\n\nimport argparse\n",
        1,
    )
    (evidence_code / "local_backend.py").write_text(producer_source)
    os.symlink(
        os.path.join(_TOOLS, "sprint_loop"),
        framework / "tools" / "sprint_loop",
    )
    (framework / "tools" / "phase-1-locks").mkdir()

    rs = _run_state(str(pilot), framework_root=str(framework))
    rs.pilot_python = sys.executable
    chunk = ChunkState(
        chunk_id="c-live-ri",
        scope="return the fixed value",
        observable_criteria=["value() returns fixed"],
        allowed_files=["app.py"],
        locked_test_files=["test_feature.py"],
        commands=[f"{sys.executable} -m pytest test_feature.py -q"],
        accepted_assertion="implementation returns fixed",
    )
    monkeypatch.setenv("EVIDENCE_SIGNING_KEY", "test-only-signing-key")

    executor_prompts: list[str] = []

    def fake_droid(role, *, options, envelope_path, stderr_path, **kwargs):
        assert role is Role.EXECUTOR
        executor_prompts.append(open(options.prompt_file).read())
        if len(executor_prompts) == 1:
            (pilot / "app.py").write_text('def value():\n    return "fixed"\n')
        with open(envelope_path, "w") as f:
            json.dump({"result": "RESULT: GREEN"}, f)
        return RunRecord(
            run_id=f"r-executor-{len(executor_prompts)}",
            role="executor",
            model_id=rs.executor.pinned_model_id,
            provider=rs.executor.pinned_provider,
            family=rs.executor.pinned_family,
            provider_lock=rs.executor.pinned_provider,
            api_provider_lock=rs.executor.pinned_provider,
            envelope_path=envelope_path,
            stderr_path=stderr_path,
        )

    validator_results = [_reject_impl_one_rejects(), _accept_result()]

    class FakeValidatorBackend:
        def __init__(self, dry_run=False):
            assert dry_run is False

        def validate(self, **kwargs):
            return validator_results.pop(0)

    monkeypatch.setattr(per_chunk_module, "invoke_droid", fake_droid)
    monkeypatch.setattr(per_chunk_module, "LocalBackend", FakeValidatorBackend)

    ev = tmp_path / "evidence"
    result = mod.run_chunk_with_retries(rs, chunk, str(ev), False, Config())

    assert result.status == ChunkStatus.ACCEPTED
    assert result.retry_count == 1
    assert len(executor_prompts) == 2
    assert "Prior rejection feedback" not in executor_prompts[0]
    assert _FINDING_A in executor_prompts[1]
    assert "verify-and-harden" in executor_prompts[1].lower()
    assert validator_results == []


def test_reject_impl_retry_stamps_feedback_source_on_chunk(tmp_path, monkeypatch):
    """The chunk's rejection_feedback_source distinguishes a finding-carrying
    retry from a gate-reason-only one."""
    mod = _load_runner_module()
    pilot = tmp_path / "pilot"
    (pilot / "test").mkdir(parents=True)
    (pilot / "test" / "test_devices.py").write_text("def test_devices():\n    assert True\n")
    rs = _run_state(str(pilot))
    chunk = _chunk()
    observed = _observed()
    _stub_loop(mod, monkeypatch, chunk, tmp_path, observed)
    results = [_reject_impl_one_rejects(), _accept_result()]
    monkeypatch.setattr(mod, "run_validators", lambda *a, **k: results.pop(0))

    ev = tmp_path / "ev"
    mod.run_chunk_with_retries(rs, chunk, str(ev), False, Config())

    assert chunk.rejection_feedback_source == FEEDBACK_SOURCE_VALIDATOR_FINDING


def test_reject_impl_dry_run_stamps_gate_reason_source(tmp_path, monkeypatch):
    """A dry-run rejection (no per-validator finding_text) stamps
    gate-reason, not validator-finding."""
    mod = _load_runner_module()
    pilot = tmp_path / "pilot"
    (pilot / "test").mkdir(parents=True)
    (pilot / "test" / "test_devices.py").write_text("def test_devices():\n    assert True\n")
    rs = _run_state(str(pilot))
    chunk = _chunk()
    observed = _observed()
    _stub_loop(mod, monkeypatch, chunk, tmp_path, observed)
    dry_result = BackendResult(
        gate=GateDecision.REJECT,
        reason="dry-run: simulated REJECT_IMPLEMENTATION",
        validators=[{"label": "v1", "verdict": "REJECT_IMPLEMENTATION"}],
    )
    results = [dry_result, _accept_result()]
    monkeypatch.setattr(mod, "run_validators", lambda *a, **k: results.pop(0))

    ev = tmp_path / "ev"
    mod.run_chunk_with_retries(rs, chunk, str(ev), False, Config())

    assert chunk.rejection_feedback_source == FEEDBACK_SOURCE_GATE_REASON


# ── REJECT_TEST does not feed the executor ───────────────────────────────


def test_reject_test_cycle_does_not_put_finding_into_executor_prompt(
    tmp_path, monkeypatch
):
    """A REJECT_TEST cycle routes to the test-designer; the executor's
    prompt must NOT carry the test-directed finding."""
    mod = _load_runner_module()
    pilot = tmp_path / "pilot"
    (pilot / "test").mkdir(parents=True)
    (pilot / "test" / "test_devices.py").write_text("def test_devices():\n    assert True\n")
    rs = _run_state(str(pilot))
    chunk = _chunk()
    observed = _observed()
    _stub_loop(mod, monkeypatch, chunk, tmp_path, observed)
    results = [_reject_test_result(), _accept_result()]
    monkeypatch.setattr(mod, "run_validators", lambda *a, **k: results.pop(0))

    ev = tmp_path / "ev"
    chunk = mod.run_chunk_with_retries(rs, chunk, str(ev), False, Config())

    assert chunk.status == ChunkStatus.ACCEPTED
    assert chunk.test_design_retry_count == 1
    # The executor ran on the first round only; its prompt from that
    # round must not carry the test-directed finding.
    prompt = (ev / "c-ri-ex-prompt.md").read_text()
    assert _FINDING_A not in prompt
    assert "Prior rejection feedback" not in prompt
    assert "{{" not in prompt


def test_reject_test_clears_stale_impl_feedback(tmp_path, monkeypatch):
    """A REJECT_TEST following a REJECT_IMPLEMENTATION must clear the stale
    implementation feedback so it does not bleed into the next executor run."""
    mod = _load_runner_module()
    pilot = tmp_path / "pilot"
    (pilot / "test").mkdir(parents=True)
    (pilot / "test" / "test_devices.py").write_text("def test_devices():\n    assert True\n")
    rs = _run_state(str(pilot))
    chunk = _chunk()
    observed = _observed()
    _stub_loop(mod, monkeypatch, chunk, tmp_path, observed, regenerated_test_is_green=False)
    # Round 1: REJECT_IMPLEMENTATION → executor retries.
    # Round 2: REJECT_TEST → test-designer runs.
    # Round 3: ACCEPT.
    results = [_reject_impl_one_rejects(), _reject_test_result(), _accept_result()]
    monkeypatch.setattr(mod, "run_validators", lambda *a, **k: results.pop(0))

    ev = tmp_path / "ev"
    chunk = mod.run_chunk_with_retries(rs, chunk, str(ev), False, Config())

    assert chunk.status == ChunkStatus.ACCEPTED
    # The stale implementation feedback was cleared when the REJECT_TEST
    # routing fired.
    assert chunk.rejection_feedback == []
    assert chunk.rejection_feedback_source == ""


# ── telemetry ────────────────────────────────────────────────────────────


def test_run_summary_row_carries_executor_feedback_source(tmp_path):
    """The role=run summary row's reject_cycles_by_chunk entries carry
    executor_feedback_source so a finding-carrying retry is distinguishable."""
    mod = _load_runner_module()
    rs = _run_state(str(tmp_path), framework_root=_REPO)
    c = ChunkState(chunk_id="c-impl", scope="s")
    c.status = ChunkStatus.HUMAN_DECISION
    c.gate_decision = GateDecision.REJECT
    c.retry_count = 1
    c.rejection_kind = "implementation"
    c.rejection_feedback_source = FEEDBACK_SOURCE_VALIDATOR_FINDING
    rs.chunks = [c]

    out = tmp_path / "runs.jsonl"
    mod.append_run_summary_row(rs, 3, str(out))
    row = json.loads(out.read_text().splitlines()[0])

    assert row["reject_cycles_by_chunk"] == [
        {"chunk_id": "c-impl", "executor_retry_count": 1,
         "test_design_retry_count": 0, "last_rejection_kind": "implementation",
         "executor_feedback_source": "validator-finding"},
    ]


def test_executor_seat_row_carries_feedback_source_note(tmp_path, monkeypatch):
    """The executor's per-call seat row stamps a note so the feedback
    source is visible at the call level, not just the run level."""
    from sprint_loop import per_chunk

    fw_root = tmp_path / "fw"
    (fw_root / "telemetry").mkdir(parents=True)
    rs = _run_state(str(tmp_path / "pilot"), framework_root=str(fw_root))
    chunk = _chunk()
    chunk.retry_count = 1
    chunk.rejection_feedback_source = FEEDBACK_SOURCE_VALIDATOR_FINDING
    ev = tmp_path / "ev"
    ev.mkdir()
    prompt = ev / "prompt.md"
    prompt.write_text("prompt")

    per_chunk.invoke_executor(
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
    assert rows[0]["role"] == "executor"
    assert "retry_feedback_source=validator-finding" in rows[0].get("note", "")


def test_executor_seat_row_no_note_on_first_attempt(tmp_path, monkeypatch):
    """A first attempt (retry_count=0) does not stamp a feedback-source note."""
    from sprint_loop import per_chunk

    fw_root = tmp_path / "fw"
    (fw_root / "telemetry").mkdir(parents=True)
    rs = _run_state(str(tmp_path / "pilot"), framework_root=str(fw_root))
    chunk = _chunk()
    # retry_count=0, rejection_feedback_source="" — first attempt.
    ev = tmp_path / "ev"
    ev.mkdir()
    prompt = ev / "prompt.md"
    prompt.write_text("prompt")

    per_chunk.invoke_executor(
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
    # The dry-run note may be present, but it must NOT carry a
    # retry_feedback_source tag — this is a first attempt.
    assert "retry_feedback_source" not in (rows[0].get("note") or "")

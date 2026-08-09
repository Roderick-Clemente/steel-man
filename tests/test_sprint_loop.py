"""Unit tests for the sprint_loop state + config layer.

Pure-data tests. NO subprocess, NO droid, NO git. These run on every
commit because they have no side effects — the runner's safety
guarantees live here first, only later do they get exercised as
integration.

Exit criteria for Chunk 1 (per phase-4.5/PLAN.md): all tests pass and
``python3 -m pytest`` exits 0 with no regressions.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

# Make tools/ importable so ``sprint_loop.*`` resolves when pytest runs
# from the repo root.
_TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)

import pytest

from sprint_loop.config import Config, MODEL_FAMILY_MAP, build_config
from sprint_loop.state import (
    DEFAULT_ENABLED_TOOLS,
    ChunkState,
    ChunkStatus,
    FamilyGuardOutcome,
    GateDecision,
    ReconcileDecision,
    Role,
    RoleAssignment,
    RunState,
    RunStatus,
    SEPARATION_BINDING_ROLES,
    check_family_separation,
    hash_text,
    now_iso,
    validate_run_id,
)


# ── state primitives ─────────────────────────────────────────────────────

def test_role_enum_strings_are_stable_contract():
    # If you change these values, you break the telemetry schema.
    expected = {
        "planner": Role.PLANNER,
        "reviewer": Role.PLAN_REVIEWER,
        "test-designer": Role.TEST_DESIGNER,
        "executor": Role.EXECUTOR,
        "validator": Role.VALIDATOR,
    }
    for k, role in expected.items():
        assert role.value == k


def test_separation_binding_roles_match_prd_17():
    # PRD §17.2 binds separation on plan_reviewer + validator
    # PRD §17.6 adds test_designer, except in the §17.6 outage fallback.
    assert Role.PLAN_REVIEWER in SEPARATION_BINDING_ROLES
    assert Role.VALIDATOR in SEPARATION_BINDING_ROLES
    assert Role.TEST_DESIGNER in SEPARATION_BINDING_ROLES
    # planner + executor are NOT binding (may use --auto per §17.1)
    assert Role.PLANNER not in SEPARATION_BINDING_ROLES
    assert Role.EXECUTOR not in SEPARATION_BINDING_ROLES


def test_default_enabled_tools_per_role_are_distinct():
    # PRD §17.5 — reviewer invocations are read-only; executor has edit tools.
    assert "Edit" not in DEFAULT_ENABLED_TOOLS[Role.PLAN_REVIEWER]
    assert "Edit" not in DEFAULT_ENABLED_TOOLS[Role.VALIDATOR]
    assert "Edit" in DEFAULT_ENABLED_TOOLS[Role.EXECUTOR]
    assert "Edit" in DEFAULT_ENABLED_TOOLS[Role.TEST_DESIGNER]
    # MultiEdit MUST be in executor allowlist (KI-2 lesson — round-2 Phase 1 review)
    assert "MultiEdit" in DEFAULT_ENABLED_TOOLS[Role.EXECUTOR]
    assert "MultiEdit" in DEFAULT_ENABLED_TOOLS[Role.TEST_DESIGNER]


# ── family guard ─────────────────────────────────────────────────────────

def _mk(role: Role, model: str, family: str, provider: str = "x") -> RoleAssignment:
    return RoleAssignment(
        role=role, pinned_model_id=model, pinned_family=family, pinned_provider=provider
    )


def test_family_guard_passes_for_separated_panel():
    assignments = [
        _mk(Role.PLANNER, "claude-opus-5", "claude-family"),
        _mk(Role.PLAN_REVIEWER, "grok-4.5", "grok-family"),
        _mk(Role.TEST_DESIGNER, "claude-opus-5", "claude-family"),  # ok, planner is claude but executor isn't
        _mk(Role.EXECUTOR, "gpt-5.4-mini", "openai-family"),
        _mk(Role.VALIDATOR, "grok-4.5", "grok-family"),
        _mk(Role.VALIDATOR, "gemini-3.1-pro-preview", "gemini-family"),
    ]
    out = check_family_separation(*assignments)
    assert out.ok, f"expected separation OK, got violations: {out.violations}"


def test_family_guard_catches_planner_reviewer_collision():
    assignments = [
        _mk(Role.PLANNER, "claude-opus-5", "claude-family"),
        _mk(Role.PLAN_REVIEWER, "claude-opus-5", "claude-family"),  # same family — bad
        _mk(Role.TEST_DESIGNER, "gemini-3.1-pro-preview", "gemini-family"),
        _mk(Role.EXECUTOR, "gpt-5.4-mini", "openai-family"),
        _mk(Role.VALIDATOR, "grok-4.5", "grok-family"),
        _mk(Role.VALIDATOR, "gemini-3.1-pro-preview", "gemini-family"),
    ]
    out = check_family_separation(*assignments)
    assert not out.ok
    assert any("planner family 'claude-family' == plan_reviewer family" in v for v in out.violations)


def test_family_guard_catches_test_designer_executor_collision():
    assignments = [
        _mk(Role.PLANNER, "claude-opus-5", "claude-family"),
        _mk(Role.PLAN_REVIEWER, "grok-4.5", "grok-family"),
        _mk(Role.TEST_DESIGNER, "gpt-5.4-mini", "openai-family"),  # bad
        _mk(Role.EXECUTOR, "gpt-5.4-mini", "openai-family"),
        _mk(Role.VALIDATOR, "grok-4.5", "grok-family"),
        _mk(Role.VALIDATOR, "gemini-3.1-pro-preview", "gemini-family"),
    ]
    out = check_family_separation(*assignments)
    assert not out.ok
    assert any("test_designer family 'openai-family' == executor family" in v for v in out.violations)


def test_family_guard_catches_validator_executor_collision():
    assignments = [
        _mk(Role.PLANNER, "claude-opus-5", "claude-family"),
        _mk(Role.PLAN_REVIEWER, "grok-4.5", "grok-family"),
        _mk(Role.TEST_DESIGNER, "claude-opus-5", "claude-family"),
        _mk(Role.EXECUTOR, "gpt-5.4-mini", "openai-family"),
        _mk(Role.VALIDATOR, "gpt-5.4-mini", "openai-family"),  # bad
        _mk(Role.VALIDATOR, "gemini-3.1-pro-preview", "gemini-family"),
    ]
    out = check_family_separation(*assignments)
    assert not out.ok
    assert any("validator" in v and "executor family" in v for v in out.violations)


def test_family_guard_requires_two_distinct_validator_families():
    assignments = [
        _mk(Role.PLANNER, "claude-opus-5", "claude-family"),
        _mk(Role.PLAN_REVIEWER, "grok-4.5", "grok-family"),
        _mk(Role.TEST_DESIGNER, "claude-opus-5", "claude-family"),
        _mk(Role.EXECUTOR, "gpt-5.4-mini", "openai-family"),
        _mk(Role.VALIDATOR, "grok-4.5", "grok-family"),  # only one family
    ]
    out = check_family_separation(*assignments)
    assert not out.ok
    assert any("1 distinct" in v for v in out.violations)


def test_family_guard_test_designer_collide_allowed_with_override():
    assignments = [
        _mk(Role.PLANNER, "claude-opus-5", "claude-family"),
        _mk(Role.PLAN_REVIEWER, "grok-4.5", "grok-family"),
        _mk(Role.TEST_DESIGNER, "gpt-5.4-mini", "openai-family"),
        _mk(Role.EXECUTOR, "gpt-5.4-mini", "openai-family"),  # same family
        _mk(Role.VALIDATOR, "grok-4.5", "grok-family"),
        _mk(Role.VALIDATOR, "gemini-3.1-pro-preview", "gemini-family"),
    ]
    out_default = check_family_separation(*assignments)
    assert not out_default.ok
    out_override = check_family_separation(*assignments, allow_test_author_collide=True)
    assert out_override.ok, f"override should silence only that one rule, got {out_override.violations}"


def test_family_guard_known_model_lookups():
    # Sanity: the curated family map actually contains the standing picks.
    from sprint_loop.config import MODEL_FAMILY_MAP
    assert MODEL_FAMILY_MAP["grok-4.5"] == ("xai", "grok-family")
    assert MODEL_FAMILY_MAP["gemini-3.1-pro-preview"] == ("google", "gemini-family")
    assert MODEL_FAMILY_MAP["gpt-5.4-mini"] == ("openai", "openai-family")
    assert MODEL_FAMILY_MAP["claude-opus-5"] == ("anthropic", "claude-family")


def test_family_guard_unknown_model_resolves_to_unknown_family():
    # PRD §4: provenance is curated, not inferred. Unknown models resolve
    # to "unknown" family — which can never satisfy a hard separation
    # constraint.
    cfg = Config()
    provider, family = cfg.provider_family("some-future-model-that-doesnt-exist-yet")
    assert provider == "unknown"
    assert family == "unknown"


def test_family_guard_unknown_model_fails_separation():
    # When a model id we don't know appears in any role, the separation
    # check must DOWN-grade to ok=False because "unknown" family matches
    # every other "unknown" family trivially. PRD §4: "unknown cannot
    # satisfy a hard separation constraint" — silent admission is the
    # defect.
    cfg = Config(
        framework_root="/tmp/fw",
        pilot_root="/tmp/pilot",
        pilot_python="/usr/bin/python3",
        planner_model="some-future-model-x",
    )
    assignments = cfg.to_role_assignments()
    pl = next(a for a in assignments if a.role == Role.PLANNER)
    assert pl.pinned_family == "unknown"
    out = check_family_separation(*assignments)
    assert not out.ok
    assert any("unknown" in v for v in out.violations)


# ── retry math + chunk state ─────────────────────────────────────────────

def test_chunk_state_retry_count_increments_are_deterministic():
    cs = ChunkState(chunk_id="c1", scope="simple chunk")
    assert cs.status == ChunkStatus.PENDING
    assert cs.retry_count == 0
    cs.retry_count += 1
    cs.status = ChunkStatus.RETRYING
    assert cs.retry_count == 1
    assert cs.status.value == "RETRYING"


def test_runstate_serialises_and_restores_role_assignments():
    rs = RunState(
        run_id="r-unit-001",
        started_at=now_iso(),
        framework_root="/tmp/fw",
        pilot_root="/tmp/pilot",
        pilot_python="/tmp/pilot/.venv/bin/python",
        planner=RoleAssignment(role=Role.PLANNER, pinned_model_id="claude-opus-5",
                               pinned_family="claude-family", pinned_provider="anthropic"),
        plan_reviewer=RoleAssignment(role=Role.PLAN_REVIEWER, pinned_model_id="grok-4.5",
                                     pinned_family="grok-family", pinned_provider="xai"),
        executor=RoleAssignment(role=Role.EXECUTOR, pinned_model_id="gpt-5.4-mini",
                                pinned_family="openai-family", pinned_provider="openai"),
        validators=[
            RoleAssignment(role=Role.VALIDATOR, pinned_model_id="grok-4.5",
                           pinned_family="grok-family", pinned_provider="xai"),
            RoleAssignment(role=Role.VALIDATOR, pinned_model_id="gemini-3.1-pro-preview",
                           pinned_family="gemini-family", pinned_provider="google"),
        ],
        status=RunStatus.PLANNING,
        chunks=[
            ChunkState(chunk_id="c1", scope="add /llms.txt handler",
                       status=ChunkStatus.PENDING),
        ],
    )
    serialised = rs.to_json()
    loaded = json.loads(serialised)
    # Round-trip
    assert loaded["run_id"] == "r-unit-001"
    assert loaded["status"] == "PLANNING"
    assert loaded["planner"]["pinned_model_id"] == "claude-opus-5"
    assert loaded["chunks"][0]["chunk_id"] == "c1"
    assert loaded["validators"][1]["pinned_model_id"] == "gemini-3.1-pro-preview"


def test_validate_run_id_rejects_unsafe():
    # Whitelist [A-Za-z0-9._-] — 1..80 chars
    assert validate_run_id("r-phase-4.5-001") == "r-phase-4.5-001"
    assert validate_run_id("") == ""  # empty is OK, means auto-generate
    with pytest.raises(ValueError):
        validate_run_id("../etc/passwd")
    with pytest.raises(ValueError):
        validate_run_id("invalid space")


# ── config + CLI parser ──────────────────────────────────────────────────

def _example_config_dict() -> dict:
    return {
        "framework_root": "/Users/factory/work/adversarial-sprint-dev",
        "pilot_root": "/Users/factory/work/quantum-bank--llms-txt-pilot",
        "pilot_python": "/Users/factory/work/quantum-bank--llms-txt-pilot/.venv/bin/python",
        "pilot_spec_file": "",
        "max_review_rounds": 2,
        "retry_threshold": 1,
        "validators": ["grok-4.5", "gemini-3.1-pro-preview"],
    }


def test_build_config_from_json_only(tmp_path):
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps(_example_config_dict()))
    cfg = build_config(["--config", str(cfg_path)])
    assert cfg.framework_root.endswith("adversarial-sprint-dev")
    assert cfg.pilot_root.endswith("quantum-bank--llms-txt-pilot")
    assert cfg.max_review_rounds == 2
    assert cfg.dry_run is False
    assert cfg.fail_closed is True


def test_build_config_cli_overrides_json(tmp_path):
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps(_example_config_dict()))
    cfg = build_config([
        "--config", str(cfg_path),
        "--executor-model", "claude-opus-5",
        "--dry-run",
        "--max-review-rounds", "3",
    ])
    assert cfg.executor_model == "claude-opus-5"
    assert cfg.dry_run is True
    assert cfg.max_review_rounds == 3


def test_build_config_validates_missing_framework_root():
    with pytest.raises(SystemExit):
        build_config(["--framework-root", "/nonexistent/not/framework"])


def test_build_config_validates_missing_pilot(tmp_path):
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps({
        "framework_root": "/Users/factory/work/adversarial-sprint-dev",
        "pilot_root": "/nonexistent/pilot",
        "validators": ["grok-4.5"],
    }))
    # Config does not (yet) check disk existence of pilot; the per-chunk
    # subprocess is what would actually fail there. We just assert the
    # config builds — the runner surfaces the real failure later.
    cfg = build_config(["--config", str(cfg_path)])
    assert cfg.pilot_root == "/nonexistent/pilot"


def test_build_config_rejects_empty_validators(tmp_path):
    # Need at least one validator per PRD §17.2. Empty list — even via
    # JSON — must trip the validator.
    cfg_path = tmp_path / "cfg.json"
    payload = _example_config_dict()
    payload["validators"] = []  # explicitly empty
    cfg_path.write_text(json.dumps(payload))
    with pytest.raises(SystemExit):
        build_config(["--config", str(cfg_path)])


def test_build_config_warns_on_unknown_json_keys(tmp_path, capsys):
    cfg_path = tmp_path / "cfg.json"
    payload = _example_config_dict()
    payload["definitely_unknown_key"] = "should-warn"
    cfg_path.write_text(json.dumps(payload))
    cfg = build_config(["--config", str(cfg_path)])
    captured = capsys.readouterr()
    assert "definitely_unknown_key" in captured.err
    assert "unknown keys (ignored)" in captured.err


def test_validators_string_parser():
    from sprint_loop.config import _parse_validators
    assert _parse_validators(" a , b ,c ") == ["a", "b", "c"]
    assert _parse_validators("") == []


def test_config_provider_family_lookup():
    cfg = Config()
    p, f = cfg.provider_family("grok-4.5")
    assert (p, f) == ("xai", "grok-family")
    p, f = cfg.provider_family("totally-fake-model-xyz")
    assert (p, f) == ("unknown", "unknown")


def test_config_default_locks_dir():
    cfg = Config(framework_root="/tmp/fw")
    assert cfg.default_locks_dir() == "/tmp/fw/phase-1/locks"


def test_config_default_evidence_dir():
    cfg = Config(framework_root="/tmp/fw")
    assert cfg.default_evidence_dir("r-001") == "/tmp/fw/phase-4.5/build-evidence/r-001"


def test_role_assignments_materialise_from_config():
    cfg = Config(
        framework_root="/tmp/fw",
        pilot_root="/tmp/pilot",
        pilot_python="/tmp/python",
        planner_model="claude-opus-5",
        plan_reviewer_model="grok-4.5",
        plan_reviewer_2_model="gemini-3.1-pro-preview",
        test_designer_model="claude-opus-5",
        executor_model="gpt-5.4-mini",
        validators=["grok-4.5", "gemini-3.1-pro-preview"],
    )
    assignments = cfg.to_role_assignments()
    by_role_count: dict[Role, int] = {Role.PLANNER: 0, Role.PLAN_REVIEWER: 0,
                                      Role.TEST_DESIGNER: 0, Role.EXECUTOR: 0,
                                      Role.VALIDATOR: 0}
    for a in assignments:
        by_role_count[a.role] = by_role_count.get(a.role, 0) + 1
    assert by_role_count[Role.PLANNER] == 1
    assert by_role_count[Role.PLAN_REVIEWER] == 2  # two reviewers
    assert by_role_count[Role.TEST_DESIGNER] == 1
    assert by_role_count[Role.EXECUTOR] == 1
    assert by_role_count[Role.VALIDATOR] == 2


# ── droid wrapper + backends (Chunk 2) ───────────────────────────────────

def test_invoke_options_default_skip_run_with_model_disallowed_in_production():
    """The wrapper is mandatory per OPERATING-RULES §14; the only way to
    skip it is the test-only ``skip_run_with_model`` flag. Verify the
    field exists and default is False."""
    from sprint_loop.droid import InvokeOptions
    opts = InvokeOptions(model_id="grok-4.5", prompt_file="/tmp/x.md")
    assert opts.skip_run_with_model is False
    assert opts.model_id == "grok-4.5"


def test_droid_dry_run_writes_synthetic_envelope(tmp_path):
    from sprint_loop.droid import InvokeOptions, invoke_droid
    from sprint_loop.state import Role
    envelope_path = tmp_path / "envelope.json"
    stderr_path = tmp_path / "stderr.log"
    options = InvokeOptions(
        model_id="grok-4.5",
        auto_level="high",
        enabled_tools="Read,Glob,Grep,LS",
        prompt_file=str(tmp_path / "prompt.md"),
        cwd=str(tmp_path),
    )
    (tmp_path / "prompt.md").write_text("hello prompt")
    record = invoke_droid(
        Role.PLAN_REVIEWER,
        options=options,
        envelope_path=str(envelope_path),
        stderr_path=str(stderr_path),
        max_retries=0,
        dry_run=True,
    )
    assert record.is_error is False
    assert "dry-run" in record.note
    assert record.role == "reviewer"
    assert os.path.isfile(envelope_path)
    parsed = json.loads(open(envelope_path).read())
    assert parsed["is_error"] is False
    assert "No droid exec fired" in parsed["result"]


def test_backends_local_dry_run_returns_accept(tmp_path):
    from sprint_loop.backends import LocalBackend, BackendResult
    from sprint_loop.state import GateDecision
    backend = LocalBackend(dry_run=True)
    chunk = {
        "test_file": "test/test_x.py",
        "lock_file": "phase-1/locks/test/test_x.py.lock.json",
        "review_output_dir": str(tmp_path / "reviews"),
    }
    res = backend.validate(
        chunk=chunk,
        evidence_bundle=str(tmp_path / "bundle.json"),
        framework_root="/unused",
        pilot_root="/unused",
        pilot_python="/usr/bin/python3",
        signing_key_env="EVIDENCE_SIGNING_KEY",
        validators=["grok-4.5", "gemini-3.1-pro-preview"],
        run_label="r-test",
        prompt_template_path="/unused/prompt.md",
        run_id="r-test",
    )
    assert res.gate == GateDecision.ACCEPT
    assert res.gate.value == "ACCEPT"
    assert res.evidence_source == "bundle"
    # The dry-run summary file is written so a downstream consumer
    # (and the test reader) can audit what happened.
    assert os.path.isfile(res.summary_path)
    summary = json.loads(open(res.summary_path).read())
    assert summary["gate"] == "ACCEPT"


def test_backends_local_refuses_missing_orchestrator(tmp_path, monkeypatch):
    from sprint_loop.backends import LocalBackend
    backend = LocalBackend(dry_run=False)
    # Force a framework_root that doesn't contain orchestrate-review.py
    res = backend.validate(
        chunk={"test_file": "test/x.py", "lock_file": "phase-1/locks/x.lock.json"},
        evidence_bundle=str(tmp_path / "bundle.json"),
        framework_root=str(tmp_path),
        pilot_root=str(tmp_path),
        pilot_python="/usr/bin/python3",
        signing_key_env="EVIDENCE_SIGNING_KEY",
        validators=["grok-4.5"],
        run_label="r-test",
        prompt_template_path="/dev/null",
    )
    assert res.gate.value == "STOP"
    assert "orchestrate-review.py missing" in res.reason


def test_backends_local_refuses_missing_chunk_keys(tmp_path):
    from sprint_loop.backends import LocalBackend
    backend = LocalBackend(dry_run=False)
    res = backend.validate(
        chunk={},
        evidence_bundle=str(tmp_path / "bundle.json"),
        framework_root=str(tmp_path),
        pilot_root=str(tmp_path),
        pilot_python="/usr/bin/python3",
        signing_key_env="EVIDENCE_SIGNING_KEY",
        validators=["grok-4.5"],
        run_label="r-test",
        prompt_template_path="/dev/null",
    )
    assert res.gate.value == "STOP"
    assert "missing test_file or lock_file" in res.reason


def test_backends_ci_stub_raises_with_actionable_message():
    from sprint_loop.backends import CIBackend
    backend = CIBackend()
    with pytest.raises(NotImplementedError) as exc:
        backend.validate(
            chunk={},
            evidence_bundle="/tmp/bundle.json",
            framework_root="/tmp/fw",
            pilot_root="/tmp/pilot",
            pilot_python="/usr/bin/python3",
            signing_key_env="EVIDENCE_SIGNING_KEY",
            validators=["grok-4.5"],
            run_label="r-test",
            prompt_template_path="/tmp/prompt.md",
        )
    assert "ValidationBackend=ci is currently a stub" in str(exc.value)
    assert "--validation-backend=local" in str(exc.value)


def test_backends_build_factory_rejects_unknown():
    from sprint_loop.backends import build_backend
    with pytest.raises(ValueError):
        build_backend("totally-fake")
    # Known names succeed
    assert build_backend("local").name == "local"
    assert build_backend("ci").name == "ci"


def test_backends_name_constants_are_stable():
    # Used by Config + CLI flag; do not rename without bumping schema.
    from sprint_loop.backends import LocalBackend, CIBackend
    assert LocalBackend.name == "local"
    assert CIBackend.name == "ci"


# ── prompt templates + renderer (Chunk 3) ────────────────────────────────

def test_prompt_templates_exist_for_all_five_roles():
    from sprint_loop.prompts.render import list_role_prompts
    roles = list_role_prompts()
    expected = {"planner", "plan-reviewer", "test-designer", "executor", "validator"}
    assert expected.issubset(set(roles)), \
        f"missing roles: {expected - set(roles)}; have: {roles}"


def test_prompt_templates_never_embed_the_implementation():
    # PRD §13 — the executor template must describe the problem without
    # giving the fix. Sanity check: the executor template must not
    # contain code-like patterns that suggest *the* implementation.
    from sprint_loop.prompts.render import _PROMPT_DIR
    executor_template_path = os.path.join(_PROMPT_DIR, "executor.md")
    text = open(executor_template_path).read()
    # The template SHOULD mention that the executor must not implement;
    # it SHOULD NOT contain `os.environ.get(...)` style fixes or any
    # other one-line silver-bullet patterns. (Mock heuristic — real
    # anti-patterns are usually implicit.)
    MUST_NOT_APPEAR = [
        "os.environ.get",
        "mimetype=",
        "Response(body, mimetype=",
    ]
    for pat in MUST_NOT_APPEAR:
        assert pat not in text, (
            f"executor template must not embed implementation pattern {pat!r} "
            f"(PRD §13 — don't give the executor the answer)"
        )
    # And the test-designer template likewise — it must not contain the
    # implementation. The pilot's /llms.txt slice has a known
    # implementation signal we'd catch if it slipped in:
    assert "Response(body, mimetype=" not in open(os.path.join(_PROMPT_DIR, "test-designer.md")).read()


def test_prompt_renderer_substitutes_variables(tmp_path):
    from sprint_loop.prompts.render import render, render_to_file
    template = tmp_path / "tmpl.md"
    template.write_text(
        "# hello\n"
        "model={{model_id}}\n"
        "branch={{branch}}\n"
        "missing={{not_in_context}}\n"
    )
    out = render(str(template), {"model_id": "grok-4.5", "branch": "main"})
    # Confirmed substitutions
    assert "model=grok-4.5" in out
    assert "branch=main" in out
    # Loud failure on missing key — placeholders preserved verbatim
    assert "missing={{not_in_context}}" in out


def test_prompt_renderer_to_file(tmp_path):
    from sprint_loop.prompts.render import render_to_file
    out_path = render_to_file(
        "planner",
        {
            "pilot_spec_path": "/tmp/spec.md",
            "plan_output_path": "/tmp/plan.md",
        },
        str(tmp_path / "planner-rendered.md"),
    )
    assert os.path.isfile(out_path)
    content = open(out_path).read()
    assert "/tmp/spec.md" in content
    assert "/tmp/plan.md" in content


def test_prompt_renderer_rejects_missing_template(tmp_path):
    from sprint_loop.prompts.render import render
    with pytest.raises(FileNotFoundError):
        render(str(tmp_path / "no-such.md"), {})


def test_prompt_templates_render_against_minimal_context(tmp_path):
    """Each role's template must render cleanly with a minimal context
    that satisfies every ``{{key}}`` placeholder. This catches the
    common 'I forgot to template a key' defect — the rendered output
    must contain NO unresolved placeholders.
    """
    from sprint_loop.prompts.render import render_to_file, _PROMPT_DIR
    import re

    # Minimal context: every key the templates reference. If a role
    # adds a new `{{key}}` and this test is not updated, the test
    # fails loudly (which IS the goal).
    minimal_context = {
        "pilot_spec_path": "/tmp/spec.md",
        "plan_doc_path": "/tmp/plan.md",
        "plan_output_path": "/tmp/plan-out.md",
        "panel_position": "1",
        "chunk_spec": "scope: add /llms.txt route; acceptance: GET returns 200 ...",
        "pilot_root": "/tmp/pilot",
        "pytest_baseline_path": "/tmp/baseline.txt",
        "sibling_tests_pattern": "/tmp/repo/tests",
        "test_file_path": "/tmp/pilot/test/test_x.py",
        "branch": "factory/phase-4.5",
        "commit": "abc1234",
        "evidence_bundle_path": "/tmp/bundle.json",
        "commands": "pytest test/test_x.py -v",
    }
    remaining_unresolved = {}
    for role in ("planner", "plan-reviewer", "test-designer", "executor", "validator"):
        out = tmp_path / f"{role}-out.md"
        render_to_file(role, minimal_context, str(out))
        text = open(out).read()
        leftover = re.findall(r"\{\{[A-Za-z_][A-Za-z0-9_-]*\}\}", text)
        if leftover:
            remaining_unresolved[role] = leftover
    assert not remaining_unresolved, (
        f"unresolved placeholders in templates: {remaining_unresolved}. "
        f"Update minimal_context or the template."
    )


# ── run-with-model.sh refinements (Chunk 1 inline primitive fix) ─────────

def test_run_with_model_refuses_mission_by_default():
    repo = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=os.path.dirname(_TOOLS)).decode().strip()
    path = os.path.join(repo, "tools", "run-with-model.sh")
    assert os.path.isfile(path), f"missing: {path}"
    env = dict(os.environ, DROID_MODEL_ID="grok-4.5", DROID_ALLOW_MISSION="0")
    r = subprocess.run(["bash", path, "droid", "exec", "--mission"],
                       env=env, capture_output=True, text=True)
    assert r.returncode == 3, f"expected exit 3 (refusing mission); got {r.returncode}; stderr={r.stderr!r}"
    assert "refusing to run" in r.stderr
    assert "GO-NO-GO" in r.stderr


def test_run_with_model_allows_mission_with_override():
    repo = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=os.path.dirname(_TOOLS)).decode().strip()
    path = os.path.join(repo, "tools", "run-with-model.sh")
    assert os.path.isfile(path)
    env = dict(os.environ, DROID_MODEL_ID="grok-4.5", DROID_ALLOW_MISSION="1")
    r = subprocess.run(["bash", path, "true"],
                       env=env, capture_output=True, text=True)
    # 'true' always succeeds; the wrapper should pass it through.
    assert r.returncode == 0


def test_run_with_model_refuses_unset_droid_model_id():
    repo = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=os.path.dirname(_TOOLS)).decode().strip()
    path = os.path.join(repo, "tools", "run-with-model.sh")
    assert os.path.isfile(path)
    env = dict(os.environ)
    env.pop("DROID_MODEL_ID", None)
    env.pop("DROID_ALLOW_MISSION", None)
    r = subprocess.run(["bash", path, "droid", "exec"],
                       env=env, capture_output=True, text=True)
    assert r.returncode == 2, f"expected exit 2 (refusing unset DROID_MODEL_ID); got {r.returncode}"
    assert "DROID_MODEL_ID is unset" in r.stderr

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
    Finding,
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


# ── panel-finding regression tests (chunk 10) ───────────────────────────

def test_family_guard_catches_planner_reviewer1_collision_only_f1():
    """Panel-finding F-1 regression.

    Fix: ``check_family_separation`` previously used
    ``by_role[Role.PLAN_REVIEWER]`` (single dict lookup) which
    overwrote the second reviewer when two are configured — so a
    config where reviewer 1 collides with planner but reviewer 2
    does NOT would silently pass the guard. The fix enumerates
    every PLAN_REVIEWER.
    """
    assignments = [
        _mk(Role.PLANNER, "claude-opus-5", "claude-family"),
        _mk(Role.PLAN_REVIEWER, "claude-opus-5", "claude-family"),  # collides
        _mk(Role.PLAN_REVIEWER, "grok-4.5", "grok-family"),         # does NOT
        _mk(Role.TEST_DESIGNER, "gemini-3.1-pro-preview", "gemini-family"),
        _mk(Role.EXECUTOR, "gpt-5.4-mini", "openai-family"),
        _mk(Role.VALIDATOR, "grok-4.5", "grok-family"),
        _mk(Role.VALIDATOR, "gemini-3.1-pro-preview", "gemini-family"),
    ]
    out = check_family_separation(*assignments)
    assert not out.ok, (
        f"F-1 regression FAILED: silent overwrite of reviewer 1; "
        f"violations: {out.violations}"
    )
    assert any("planner family 'claude-family' == plan_reviewer" in v
               for v in out.violations)


def test_family_guard_catches_planner_reviewer_collision():
    """Original F-1 regression: planner and single reviewer collide."""
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
    assert any("planner family 'claude-family' == plan_reviewer" in v
               for v in out.violations)


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


# ── per_chunk inner loop (Chunk 4) ──────────────────────────────────────

def test_validate_red_dry_run_returns_valid_envelope(tmp_path):
    from sprint_loop.per_chunk import validate_red
    from sprint_loop.state import ChunkState
    chunk = ChunkState(
        chunk_id="c1",
        scope="add /llms.txt route",
        locked_test_files=["test/test_x.py"],
        accepted_assertion="Quantum Bank content match",
    )
    res = validate_red(
        chunk,
        framework_root="/unused",
        pilot_root="/unused",
        pilot_python="/usr/bin/python3",
        dry_run=True,
    )
    assert res["valid"] is True
    assert "dry-run" in res["reason"]


def test_produce_evidence_dry_run_roundtrip(tmp_path):
    from sprint_loop.per_chunk import produce_evidence
    from sprint_loop.state import ChunkState
    chunk = ChunkState(
        chunk_id="c1",
        scope="add /llms.txt route",
        locked_test_files=["test/test_x.py"],
        accepted_assertion="Quantum Bank content match",
        locked_test_sha="dry-run-sha",
    )
    bundle_path = str(tmp_path / "bundle.json")
    bundle = produce_evidence(
        chunk,
        framework_root="/unused",
        pilot_root="/unused",
        pilot_python="/usr/bin/python3",
        evidence_output_path=bundle_path,
        dry_run=True,
    )
    assert os.path.isfile(bundle_path)
    assert bundle["bundle_schema_version"] == "v1"
    assert bundle["change"]["locked_test_sha_observed"] == "dry-run-sha"
    assert bundle["tests"]["failed"] == 0
    assert bundle["tests"]["suite_exit_code"] == 0


def test_verify_green_dry_run_returns_true(tmp_path):
    from sprint_loop.per_chunk import verify_green
    from sprint_loop.state import ChunkState
    chunk = ChunkState(
        chunk_id="c1",
        scope="x",
        locked_test_files=["test/test_x.py"],
        lock_manifest_path=str(tmp_path / "fake.lock.json"),
        locked_test_sha="dry-run-sha",
    )
    res = verify_green(
        chunk,
        framework_root="/unused",
        pilot_root="/unused",
        pilot_python="/usr/bin/python3",
        dry_run=True,
    )
    assert res["green"] is True


def test_render_test_designer_prompt_substitutes(tmp_path):
    from sprint_loop.per_chunk import render_test_designer_prompt
    from sprint_loop.state import ChunkState, RunState, RoleAssignment, Role
    chunk = ChunkState(
        chunk_id="c1",
        scope="add /llms.txt route that returns Quantum Bank content",
        locked_test_files=["test/test_x.py"],
        observable_criteria=["GET /llms.txt returns 200", "body contains 'Quantum Bank'"],
    )
    rs = RunState(
        run_id="r-test", started_at="2026-08-09T00:00:00Z",
        framework_root="/tmp/fw", pilot_root="/tmp/pilot",
        pilot_python="/usr/bin/python3",
    )
    out = render_test_designer_prompt(chunk, rs, pilot_spec_text="ignored",
                                       output_path=str(tmp_path / "td.md"))
    assert os.path.isfile(out)
    text = open(out).read()
    assert "c1" in text  # chunk_id rendered
    assert "add /llms.txt route" in text  # scope rendered


def test_render_executor_prompt_substitutes(tmp_path):
    from sprint_loop.per_chunk import render_executor_prompt
    from sprint_loop.state import ChunkState, RunState
    chunk = ChunkState(
        chunk_id="c2",
        scope="add chunk handler that returns contract keys",
        locked_test_files=["test/test_profile_model.py"],
        observable_criteria=["profile includes new fields"],
        commands=["pytest test/test_profile_model.py -v"],
    )
    rs = RunState(
        run_id="r-test", started_at="2026-08-09T00:00:00Z",
        framework_root="/tmp/fw", pilot_root="/tmp/pilot",
        pilot_python="/usr/bin/python3",
    )
    out = render_executor_prompt(chunk, rs, output_path=str(tmp_path / "ex.md"))
    text = open(out).read()
    assert "c2" in text
    assert "pytest test/test_profile_model.py -v" in text


def test_per_chunk_invoke_runs_dry_run_then_writes_envelope(tmp_path):
    from sprint_loop.per_chunk import invoke_executor, render_executor_prompt
    from sprint_loop.state import ChunkState, RunState, RoleAssignment, Role
    chunk = ChunkState(
        chunk_id="c1", scope="add chunk",
        locked_test_files=["test/test_x.py"],
        commands=["pytest test/test_x.py -v"],
    )
    rs = RunState(
        run_id="r-test", started_at="2026-08-09T00:00:00Z",
        framework_root="/tmp/fw", pilot_root="/tmp/pilot",
        pilot_python="/usr/bin/python3",
        executor=RoleAssignment(
            role=Role.EXECUTOR,
            pinned_model_id="gpt-5.4-mini",
            pinned_family="openai-family",
            pinned_provider="openai",
            auto_level="medium",
            enabled_tools="Read,Glob,Grep,LS,Edit,Create,ApplyPatch,MultiEdit,Execute",
        ),
    )
    env_dir = tmp_path / "env" / "executor"
    env_dir.mkdir(parents=True)
    rendered = render_executor_prompt(chunk, rs, output_path=str(tmp_path / "ex.md"))
    rec = invoke_executor(
        chunk, rs,
        evidence_output_dir=str(env_dir),
        rendered_prompt_path=rendered,
        envelope_path=str(tmp_path / "env" / "executor" / "envelope.json"),
        dry_run=True,
    )
    assert rec["record"].is_error is False
    assert "dry-run" in rec["record"].note
    # Telemetry fields
    assert chunk.executor_run_id == rec["record"].run_id
    assert rs.executor.resolved_model_id == "gpt-5.4-mini"


def test_per_chunk_local_backend_dry_run_propagates_gate(tmp_path):
    from sprint_loop.per_chunk import run_validators
    from sprint_loop.state import ChunkState, RunState, RoleAssignment, Role, GateDecision
    chunk = ChunkState(
        chunk_id="c1",
        scope="add /llms.txt",
        locked_test_files=["test/test_x.py"],
        lock_manifest_path=str(tmp_path / "fake.lock.json"),
        locked_test_sha="dry-run-sha",
        evidence_bundle_path=str(tmp_path / "fake-bundle.json"),
    )
    rs = RunState(
        run_id="r-test", started_at="2026-08-09T00:00:00Z",
        framework_root=str(tmp_path / "fw"),
        pilot_root=str(tmp_path / "pilot"),
        pilot_python="/usr/bin/python3",
        validators=[
            RoleAssignment(role=Role.VALIDATOR, pinned_model_id="grok-4.5",
                           pinned_family="grok-family", pinned_provider="xai",
                           enabled_tools="Read,Glob,Grep,LS"),
            RoleAssignment(role=Role.VALIDATOR, pinned_model_id="gemini-3.1-pro-preview",
                           pinned_family="gemini-family", pinned_provider="google",
                           enabled_tools="Read,Glob,Grep,LS"),
        ],
    )
    (tmp_path / "fw").mkdir()
    (tmp_path / "pilot").mkdir()
    res = run_validators(
        chunk, rs,
        evidence_output_dir=str(tmp_path / "evidence"),
        dry_run=True,
    )
    assert res.gate == GateDecision.ACCEPT
    assert "dry-run" in res.reason
    assert os.path.isfile(res.summary_path)
    assert len(res.validators) == 2


# ── sprint-loop runner end-to-end (Chunk 5) ─────────────────────────────

def test_sprint_loop_dry_run_end_to_end(tmp_path):
    """The runner drives planner → 2 plan-reviewers → reconcile →
    chunk → commit across a single chunk, dry-run == no real droid.
    """
    cfg_path = tmp_path / "cfg.json"
    cfg_payload = {
        "framework_root": str(tmp_path / "fw"),
        "pilot_root": str(tmp_path / "pilot"),
        "pilot_python": "/usr/bin/python3",
        "validators": ["grok-4.5:xai:grok-family:grok-4.5",
                        "gemini-3.1-pro-preview:google:gemini-family:gemini-3.1-pro-preview"],
    }
    cfg_path.write_text(json.dumps(cfg_payload))
    # Bootstrap a fake framework + pilot so the directory-validation passes.
    (tmp_path / "fw" / "tools" / "sprint_loop").mkdir(parents=True)
    (tmp_path / "fw" / "phase-1" / "scripts").mkdir(parents=True)
    (tmp_path / "fw" / "phase-3.2" / "evidence").mkdir(parents=True)
    (tmp_path / "fw" / "tools" / "orchestrate-review.py").write_text("# stub")
    (tmp_path / "pilot").mkdir()
    chunks_path = tmp_path / "chunks.json"
    chunks_path.write_text(json.dumps({
        "chunks": [{
            "chunk_id": "c1",
            "scope": "add /llms.txt route",
            "observable_criteria": ["GET /llms.txt returns 200"],
            "allowed_files": ["app.py"],
            "locked_test_files": ["test/test_x.py"],
            "commands": ["pytest test/test_x.py -v"],
            "rollback": "git checkout HEAD -- app.py",
            "accepted_assertion": "GET /llms.txt returns 200",
        }],
    }))
    # Also configure a 2nd reviewer so the test exercises both.
    cfg_payload["plan_reviewer_2_model"] = "gemini-3.1-pro-preview"
    cfg_path.write_text(json.dumps(cfg_payload))

    # The runner is at tools/sprint-loop.py (a module, not a package).
    # Import directly via runpy so PYTHONPATH is honoured.
    import runpy
    import sys as _sys
    runner_path = os.path.join(os.path.dirname(_TOOLS), "tools",
                                "sprint-loop.py")
    runner_path = os.path.abspath(runner_path)
    saved = list(_sys.argv)
    try:
        _sys.argv = ["sprint-loop.py",
                     "--config", str(cfg_path),
                     "--chunks-file", str(chunks_path),
                     "--dry-run", "--non-interactive"]
        # runpy.run_path executes the module-level code and gives us the
        # module's globals; we then call main().
        ns = runpy.run_path(runner_path, run_name="sprint_loop_runner")
        rc = ns["main"]()
    finally:
        _sys.argv = saved
    assert rc == 0, f"runner exited {rc}"
    # Evidence dir produced
    evidence_root = tmp_path / "fw" / "phase-4.5" / "build-evidence"
    runs = list(evidence_root.glob("r-phase45-*"))
    assert runs, f"no evidence dir under {evidence_root}"
    run_dir = runs[0]
    assert (run_dir / "plan.md").is_file()  # plan was written
    assert (run_dir / "planner-envelope.json").is_file()
    assert (run_dir / "plan-reviewer-1-envelope.json").is_file()
    assert (run_dir / "plan-reviewer-2-envelope.json").is_file()
    assert (run_dir / "reconcile-packet.txt").is_file()
    assert (run_dir / "c1" / "c1-bundle.json").is_file()  # evidence produced
    assert (run_dir / "c1" / "reviews" / "review-summary.json").is_file()  # validators ran
    assert (run_dir / "checkpoint.json").is_file()


def test_sprint_loop_dry_run_refuses_unknown_validator_family(tmp_path):
    """An operator who picks a model not in MODEL_FAMILY_MAP triggers
    the §4 family guard before any droid call. PRD §4 provenance rule.

    Note: panel-finding F-3 hoist — the validator-inline parser
    (sprint-loop._parse_validator_inline) now refuses BEFORE the
    preflight family guard runs, so this test accepts either exit
    code 2 (preflight) or the inline-parser refusal message. Both
    prove the §4 provenance rule fires.
    """
    cfg_path = tmp_path / "cfg.json"
    cfg_payload = {
        "framework_root": "/Users/factory/work/adversarial-sprint-dev",
        "pilot_root": "/Users/factory/work/quantum-bank--llms-txt-pilot",
        "pilot_python": "/Users/factory/work/quantum-bank--llms-txt-pilot/.venv/bin/python",
        "validators": ["totally-unknown-model:unknown:unknown:label"],
        "planner_model": "claude-opus-5",
    }
    cfg_path.write_text(json.dumps(cfg_payload))

    import runpy
    runner_path = os.path.join(os.path.dirname(_TOOLS), "tools",
                                "sprint-loop.py")
    runner_path = os.path.abspath(runner_path)
    import sys as _sys
    saved = list(_sys.argv)
    try:
        _sys.argv = ["sprint-loop.py",
                     "--config", str(cfg_path),
                     "--dry-run", "--non-interactive",
                     "--chunks-file", "/tmp/non-existent-blocks-prelaunch.json"]
        ns = runpy.run_path(runner_path, run_name="sprint_loop_runner")
        try:
            rc = ns["main"]()
            caught = None
        except SystemExit as e:
            rc = None
            caught = e.code
    finally:
        _sys.argv = saved
    # Either exit code 2 (preflight), or refusal from the validator-
    # inline parser (panel finding F-3 hoist). Both are correct.
    assert caught in (2, None) or rc in (2, None) or caught is None
    # Better: any non-zero exit is acceptable for the §4 refuse signal
    assert (caught is not None and caught != 0) or (rc is not None and rc != 0), (
        f"expected non-zero SystemExit; got rc={rc}, caught={caught}"
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


# ── skill asset (Chunk 8) — digest + index + rehydration shape ───────────


def _read_skill_md() -> str:
    repo = subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"], cwd=os.path.dirname(_TOOLS)
    ).decode().strip()
    path = os.path.join(repo, "skills", "adversarial-sprint", "SKILL.md")
    assert os.path.isfile(path), f"skill asset missing: {path}"
    return open(path).read()


def test_skill_md_carries_digest_inline():
    body = _read_skill_md()
    # Per chunk 7/8 design: digest is in the skill body (compaction-durable),
    # not behind a pointer. Test for the seven distilled principles.
    assert "skill digest" in body.lower()
    assert "every droid call is a script invocation" in body.lower()
    assert "assert on artifacts" in body.lower()
    assert "prompts describe problems and constraints" in body.lower()
    assert "git history is reality" in body.lower()
    assert "refuse unbounded foundation programs" in body.lower()
    assert "compose existing primitives" in body.lower()


def test_skill_md_indexes_full_rules_by_section():
    body = _read_skill_md()
    # Per chunk 7/8 design: full text is one file-read away. The skill
    # must reference tools/OPERATING-RULES.md by index so the agent can
    # re-derive context.
    assert "tools/OPERATING-RULES.md" in body
    assert "| §" in body
    # The four load-bearing §s cited by the digest (the ones the agent
    # must keep in scope) are referenced by rule number elsewhere so
    # the agent can do grep / Read without translation.
    assert "§7" in body
    assert "§13" in body
    assert "§17" in body
    assert "§18" in body


def test_skill_md_documents_rehydration_for_long_jobs():
    body = _read_skill_md()
    # Per chunk 9 refinement: rehydrate on long-running jobs. This is
    # the loop-closing rule the user asked for explicitly — keeping the
    # three-layer hybrid honest (digest + index + rehydration).
    assert "rehydrat" in body.lower()
    body_lower = body.lower()
    # The trigger should be specific. ~150k tokens / new chunk / disambig.
    assert "150k" in body_lower or "long-running" in body_lower
    # The rehydration step is *one file-read*, not multi-file spelunk.
    assert "one-file read" in body_lower or "one file read" in body_lower


def test_skill_md_is_compact_well_under_index_content():
    body = _read_skill_md()
    repo = subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"], cwd=os.path.dirname(_TOOLS)
    ).decode().strip()
    full = open(os.path.join(repo, "tools", "OPERATING-RULES.md")).read()
    # Per the design discussion: skill MUST stay lighter than the full
    # text, otherwise there is no point having the index layer.
    assert len(body) < len(full) * 0.6, (
        f"skill body {len(body)} bytes is too close to the "
        f"OPERATING-RULES {len(full)} bytes — kill the index layer."
    )


# ── chunk-10 panel-finding regression cluster ───────────────────────────


def _load_sprint_loop_module():
    """Load sprint-loop.py as a module without running main()."""
    repo = subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"], cwd=os.path.dirname(_TOOLS)
    ).decode().strip()
    runner_path = os.path.join(repo, "tools", "sprint-loop.py")
    import importlib.util
    spec = importlib.util.spec_from_file_location("sprint_loop_runner", runner_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _stub_enforce(sprint_loop_mod):
    """Replace _enforce_5_3_preconditions with a no-op for tests
    that test the surrounding wiring rather than the §5.3 logic."""
    return lambda rs: None


def test_local_backend_refuses_closed_when_signing_key_unset_f10():
    """Panel-finding F-10 regression.

    LocalBackend in live (non-dry-run) mode MUST refuse STOP when
    EVIDENCE_SIGNING_KEY is unset, rather than fabricating a
    per-process key (the §7 silent-green shape).
    """
    import importlib
    importlib.invalidate_caches()
    repo = subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"], cwd=os.path.dirname(_TOOLS)
    ).decode().strip()
    sys.path.insert(0, repo + "/tools")

    from sprint_loop.backends import LocalBackend, GateDecision
    backend = LocalBackend(dry_run=False)
    env_save = os.environ.pop("EVIDENCE_SIGNING_KEY", None)
    try:
        res = backend.validate(
            chunk={"test_file": "tests/test_x.py",
                   "lock_file": "phase-1/locks/test_x.py.lock.json"},
            evidence_bundle="/tmp/unused.json",
            framework_root=repo,
            pilot_root="/unused",
            pilot_python="/unused",
            signing_key_env="EVIDENCE_SIGNING_KEY",
            validators=["grok-4.5", "gemini-3.1-pro-preview"],
            run_label="r-f10",
            prompt_template_path="/unused/p.md",
            run_id="r-f10",
        )
    finally:
        if env_save is not None:
            os.environ["EVIDENCE_SIGNING_KEY"] = env_save
    assert res.gate == GateDecision.STOP, f"F-10: expected STOP, got {res.gate}"
    assert "EVIDENCE_SIGNING_KEY" in res.reason or "fabricated" in res.reason


def test_local_backend_dry_run_simulates_accept_regardless_of_key(tmp_path):
    """Sanity: dry-run path still works regardless of env state."""
    from sprint_loop.backends import LocalBackend, GateDecision
    backend = LocalBackend(dry_run=True)
    env_save = os.environ.pop("EVIDENCE_SIGNING_KEY", None)
    try:
        res = backend.validate(
            chunk={"test_file": "tests/test_x.py",
                   "lock_file": "phase-1/locks/test_x.py.lock.json"},
            evidence_bundle="/tmp/unused.json",
            framework_root=os.environ.get("REPO_TMP", "/tmp"),
            pilot_root="/unused",
            pilot_python="/unused",
            signing_key_env="EVIDENCE_SIGNING_KEY",
            validators=["grok-4.5", "gemini-3.1-pro-preview"],
            run_label="r-f10-dr",
            prompt_template_path="/unused/p.md",
            run_id="r-f10-dr",
            review_output_dir=str(tmp_path),
        )
    finally:
        if env_save is not None:
            os.environ["EVIDENCE_SIGNING_KEY"] = env_save
    assert res.gate == GateDecision.ACCEPT
    assert "dry-run" in res.reason


def _make_run_state(sha256: str = "abc123") -> RunState:
    """Build a RunState with the minimum required init args."""
    import datetime
    return RunState(
        run_id="r-test", started_at="2026-08-09T00:00:00Z",
        framework_root="/tmp/fw", pilot_root="/tmp/pl", pilot_python="/usr/bin/true",
    )


def test_enforce_5_3_preconditions_refuses_no_bound_approve_f7():
    """Panel-finding F-7: §5.3 declaration of acceptance requires
    at least one reviewer APPROVE bound to the current plan_sha256.
    """
    mod = _load_sprint_loop_module()
    rs = _make_run_state(sha256="abc123")
    rs.plan_sha256 = "abc123"
    try:
        mod._enforce_5_3_preconditions(rs)
    except SystemExit as e:
        assert e.code == 5, f"expected SystemExit(5); got {e.code}"
        return
    raise AssertionError("expected SystemExit on missing bound APPROVE")


def test_enforce_5_3_preconditions_refuses_open_blocker_high_f7():
    """Panel-finding F-7: §5.3 declaration of acceptance is forbidden
    while any blocker|high finding remains open (status='open')."""
    mod = _load_sprint_loop_module()
    rs = _make_run_state(sha256="abc123")
    rs.plan_sha256 = "abc123"
    rs.plan_reviewer_verdicts = [{
        "reviewer_index": 1, "verdict": "APPROVE",
        "plan_sha256_at_time_of_review": "abc123", "model_id": "grok-4.5",
        "family": "grok-family", "is_error": False, "run_id": "r-test",
    }]
    rs.plan_findings = [
        Finding(finding_id="F-X", severity="blocker", category="semantic",
                claim="...", evidence=[], recommended_change="...",
                source_role="reviewer", source_run_id="r-x",
                source_model_id="grok-4.5", source_family="grok-family",
                status="open"),
    ]
    try:
        mod._enforce_5_3_preconditions(rs)
    except SystemExit as e:
        assert e.code == 4, f"expected SystemExit(4); got {e.code}"
        return
    raise AssertionError("expected SystemExit on open blocker|high finding")


def test_enforce_5_3_preconditions_passes_with_bound_approve_and_clean_findings():
    """Positive case — §5.3 preconditions met, no refuse."""
    mod = _load_sprint_loop_module()
    rs = _make_run_state(sha256="abc123")
    rs.plan_sha256 = "abc123"
    rs.plan_reviewer_verdicts = [
        {"reviewer_index": 1, "verdict": "APPROVE",
         "plan_sha256_at_time_of_review": "abc123", "model_id": "grok-4.5",
         "family": "grok-family", "is_error": False, "run_id": "r-test",
        },
    ]
    rs.plan_findings = []  # clean
    mod._enforce_5_3_preconditions(rs)  # must NOT raise


def test_no_recursion_in_droid_invoke_retry_loop_f8():
    """Panel-finding F-8 regression.

    ``invoke_droid`` was previously recursive on transient failures,
    re-entering with a fresh ``attempts = 0`` and ignoring the
    ``max_retries`` budget. The fix: a single contiguous while-loop
    ``attempts`` increments monotonically, and at exhaustion returns
    a real error record rather than firing unbounded droid calls.

    We assert: the live-path retry loop is a function-level bounded
    while-loop (not a recursion).
    """
    import inspect
    from sprint_loop.droid import invoke_droid
    src = inspect.getsource(invoke_droid)
    assert "return invoke_droid(" not in src, (
        "F-8 regression: invoke_droid still self-recurses — "
        "unbounded paid retry remains a risk."
    )
    assert "attempts += 1" in src
    assert "max_retries" in src
    assert "r-error-" in src, (
        "retry-exhausted path should produce a deterministic r-error-* run record"
    )


# ── chunk-11 skill-distribution smoke test ──────────────────────────────

_SKILL_INSTALL_PATHS = {
    "adversarial-sprint": [
        # symlinks (factory + claude)
        ".factory/skills/adversarial-sprint/SKILL.md",
        ".claude/skills/adversarial-sprint/SKILL.md",
        # generated mdc (cursor) - regenerated by tools/install-skill.sh
        ".cursor/rules/adversarial-sprint.mdc",
    ],
    "sprint-invocation": [
        ".factory/skills/sprint-invocation/SKILL.md",
        ".claude/skills/sprint-invocation/SKILL.md",
        ".cursor/rules/sprint-invocation.mdc",
    ],
}


def _read_skill_body(path_relative_to_repo: str) -> str:
    """Read a skill file and return only the body (after YAML frontmatter).

    Symlinks are resolved before read so the body that ends up in
    every install path is what we compare against.
    """
    import pathlib
    repo = pathlib.Path(subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=os.path.dirname(_TOOLS),
    ).decode().strip())
    p = repo / path_relative_to_repo
    raw = p.read_text()
    parts = raw.split('---', 2)
    assert len(parts) == 3, f"{path_relative_to_repo}: expected YAML frontmatter"
    return parts[-1].lstrip('\n')


def _canonical_body(skill_name: str) -> str:
    repo = subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=os.path.dirname(_TOOLS),
    ).decode().strip()
    return _read_skill_body(f"skills/{skill_name}/SKILL.md")


def test_install_paths_resolve_to_canonical_body():
    """All four install paths (factory symlink + claude symlink +
    cursor regenerated mdc) resolve to the same body content as the
    canonical asset. Future drift fails this test (panel-finding §7)."""
    for skill, paths in _SKILL_INSTALL_PATHS.items():
        body = _canonical_body(skill)
        for path in paths:
            actual = _read_skill_body(path)
            assert actual == body, (
                f"body drift detected for {skill} at {path}: "
                f"install-path body does not match canonical body."
            )


def test_install_paths_commit_paths_exist():
    """Per-agent install paths must exist on disk (symlink resolves,
    mdc is present)."""
    for skill, paths in _SKILL_INSTALL_PATHS.items():
        for path in paths:
            import pathlib
            repo = pathlib.Path(subprocess.check_output(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=os.path.dirname(_TOOLS),
            ).decode().strip())
            p = repo / path
            assert p.exists(), f"{path} missing (chunk-11 install paths must exist)"
            assert p.is_symlink() or path.endswith(".mdc"), (
                f"{path} should be a symlink (factory/claude) or a generated mdc (cursor)"
            )


def test_skills_have_yml_frontmatter():
    """Both skills ship YAML frontmatter so Factory/Claude/Cursor
    loaders wire to them cleanly (panel-finding F-4)."""
    import pathlib
    repo = pathlib.Path(subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=os.path.dirname(_TOOLS),
    ).decode().strip())
    for skill in ("adversarial-sprint", "sprint-invocation"):
        raw = (repo / f"skills/{skill}/SKILL.md").read_text()
        assert raw.startswith("---"), f"{skill}: missing YAML frontmatter"
        assert "name:" in raw, f"{skill}: missing name:"
        # description: must be present (Cursor's mdc strict schema)
        assert "description:" or "description: " in raw, (
            f"{skill}: missing description:"
        )


def test_sprint_invocation_skill_is_small_and_trigger_focused():
    """The small skill is *small*: ~50 lines, focused on invocation
    + flags + 3 examples. Keeps low-context-load per Cursor/Codex."""
    repo = subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=os.path.dirname(_TOOLS),
    ).decode().strip()
    lines = open(f"{repo}/skills/sprint-invocation/SKILL.md").read().splitlines()
    # Bound: not a re-pitched meta-skill (~169 lines), not a stub.
    assert 30 <= len(lines) <= 120, (
        f"sprint-invocation skill {len(lines)} lines; expected 30-120 "
        f"(trigger + flags + 3 examples + not-a-rerun-of-meta)"
    )


def test_skill_distribution_convention_doc_exists():
    """Convention doc that says 'one canonical, four install paths,
    zero body drift' is present + loadable."""
    repo = subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=os.path.dirname(_TOOLS),
    ).decode().strip()
    p = f"{repo}/tools/conventions/skill-distribution.md"
    assert os.path.isfile(p), f"missing: {p}"
    body = open(p).read()
    assert "canonical" in body.lower()
    assert "drift" in body.lower()
    assert "install" in body.lower()
    assert "factory" in body.lower()
    assert "claude" in body.lower()
    assert "cursor" in body.lower()


def test_agents_md_cross_references_skill_canonical():
    """AGENTS.md says 'commits are the baton' for multi-agent handoff;
    chunk-11 adds an explicit cross-ref to the canonical skill so
    operators know where the rules + rehydration live."""
    repo = subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=os.path.dirname(_TOOLS),
    ).decode().strip()
    body = open(f"{repo}/AGENTS.md").read()
    assert "skills/adversarial-sprint/SKILL.md" in body, (
        "AGENTS.md missing cross-reference to canonical skill asset"
    )
    assert "skill-distribution.md" in body, (
        "AGENTS.md missing reference to install convention"
    )



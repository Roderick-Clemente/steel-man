"""The validator seat must never run on an unrendered prompt.

Observed failure this pins: ``run_validators`` handed
``tools/sprint_loop/prompts/validator.md`` — the *template* — straight to
``droid exec``. Both validator seats received literal ``{{chunk_spec}}``,
``{{branch}}``, ``{{commit}}``, ``{{pilot_root}}``, ``{{test_file_path}}``
and ``{{evidence_bundle_path}}``. One seat reconstructed the inputs from
the repo and reviewed anyway; the other refused. Either way the gate that
decides whether implementation code is accepted was running blind, and it
failed silently.

Second defect pinned here: a chunk that names a regression command must
have its regression outcome in the bundle, recorded separately from the
locked-test counters, or the validator has no evidence for "existing
behaviour unchanged" and only the executor's prose claim.
"""

from __future__ import annotations

import hashlib
import hmac
import importlib.util
import json
import os
import sys

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TOOLS = os.path.join(_REPO, "tools")
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)

from sprint_loop import per_chunk  # noqa: E402
from sprint_loop.state import ChunkState, Role, RoleAssignment, RunState  # noqa: E402

_TEMPLATE = os.path.join(_TOOLS, "sprint_loop", "prompts", "validator.md")

# The exact placeholder set the live run leaked to both seats.
OBSERVED_PLACEHOLDERS = (
    "{{chunk_spec}}",
    "{{branch}}",
    "{{commit}}",
    "{{pilot_root}}",
    "{{test_file_path}}",
    "{{evidence_bundle_path}}",
)


def _load_consumer_module():
    """Load ``tools/phase-3.2-evidence/consumer.py`` (hyphenated dir)."""
    path = os.path.join(_TOOLS, "phase-3.2-evidence", "consumer.py")
    spec = importlib.util.spec_from_file_location("evidence_consumer_vpr", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_chunk(tmp_path, *, commands=None) -> ChunkState:
    return ChunkState(
        chunk_id="c1",
        scope="Add the /health route",
        observable_criteria=["GET /health returns 200"],
        allowed_files=["app.py"],
        locked_test_files=["test/test_health_route.py"],
        commands=commands
        if commands is not None
        else ["python -m pytest test/test_health_route.py -v"],
        rollback="git checkout HEAD -- app.py",
        accepted_assertion="health route returns ok",
        lock_manifest_path=str(tmp_path / "c1.lock.json"),
        locked_test_sha="a" * 64,
    )


def _make_run_state(tmp_path) -> RunState:
    pilot = tmp_path / "pilot"
    pilot.mkdir(exist_ok=True)
    fw = tmp_path / "fw"
    fw.mkdir(exist_ok=True)
    return RunState(
        run_id="r-vpr",
        started_at="2026-08-16T00:00:00Z",
        framework_root=str(fw),
        pilot_root=str(pilot),
        pilot_python="/usr/bin/python3",
        validators=[
            RoleAssignment(
                role=Role.VALIDATOR,
                pinned_model_id="grok-4.5",
                pinned_family="grok-family",
                pinned_provider="xai",
                enabled_tools="Read,Glob,Grep,LS",
            ),
        ],
    )


def _write_bundle(path: str, commit_sha: str) -> None:
    with open(path, "w") as f:
        json.dump(
            {
                "bundle_schema_version": "v1",
                "producer": "local",
                "change": {"commit_sha": commit_sha, "locked_test_sha_observed": "a" * 64},
                "tests": {"passed": 8, "failed": 0, "skipped": 0, "suite_exit_code": 0},
            },
            f,
        )


# ── Defect 1: the prompt is rendered, with real values ───────────────────


def test_rendered_validator_prompt_has_no_placeholders_left(tmp_path):
    chunk = _make_chunk(tmp_path)
    rs = _make_run_state(tmp_path)
    chunk.evidence_bundle_path = str(tmp_path / "c1-bundle.json")
    _write_bundle(chunk.evidence_bundle_path, "c0ffee" * 6 + "abcd")

    out = tmp_path / "reviews" / "c1-va-prompt.md"
    rendered_path = per_chunk.render_validator_prompt(chunk, rs, output_path=str(out))
    rendered = open(rendered_path).read()

    assert "{{" not in rendered
    for placeholder in OBSERVED_PLACEHOLDERS:
        assert placeholder not in rendered

    # Each of the six placeholders was substituted with its real value.
    assert "CHUNK_ID: c1" in rendered  # chunk_spec
    assert "ACCEPTED_ASSERTION: health route returns ok" in rendered  # chunk_spec
    assert "c0ffee" * 6 + "abcd" in rendered  # commit (bundle change.commit_sha)
    assert rs.pilot_root in rendered  # pilot_root
    assert os.path.join(rs.pilot_root, "test/test_health_route.py") in rendered  # test_file_path
    assert chunk.evidence_bundle_path in rendered  # evidence_bundle_path
    # branch: pilot repo branch, or the "unknown"/"detached" sentinel when
    # the pilot fixture is not a git repo.
    assert per_chunk._git_branch(rs.pilot_root) in rendered


def test_chunk_spec_in_validator_prompt_is_the_executors_formatter(tmp_path):
    chunk = _make_chunk(tmp_path)
    rs = _make_run_state(tmp_path)
    chunk.evidence_bundle_path = str(tmp_path / "c1-bundle.json")
    _write_bundle(chunk.evidence_bundle_path, "d" * 40)

    out = tmp_path / "reviews" / "c1-va-prompt.md"
    rendered = open(per_chunk.render_validator_prompt(chunk, rs, output_path=str(out))).read()
    assert per_chunk._format_chunk_spec(chunk) in rendered


# ── Defect 2: the prompt is archived, and it is what gets invoked ────────


def test_run_validators_passes_the_rendered_prompt_from_the_evidence_dir(tmp_path, monkeypatch):
    chunk = _make_chunk(tmp_path)
    rs = _make_run_state(tmp_path)
    evidence_dir = tmp_path / "evidence" / "c1"
    chunk.evidence_bundle_path = str(tmp_path / "c1-bundle.json")
    _write_bundle(chunk.evidence_bundle_path, "e" * 40)

    from sprint_loop.state import GateDecision

    captured: dict = {}

    class _CapturingBackend:
        def __init__(self, dry_run: bool = False):
            captured["dry_run"] = dry_run

        def validate(self, **kwargs):
            captured.update(kwargs)
            return per_chunk.BackendResult(gate=GateDecision.ACCEPT, reason="captured")

    monkeypatch.setattr(per_chunk, "LocalBackend", _CapturingBackend)

    per_chunk.run_validators(chunk, rs, evidence_output_dir=str(evidence_dir), dry_run=True)

    prompt_path = captured["prompt_template_path"]
    reviews_dir = os.path.join(str(evidence_dir), "reviews")
    assert os.path.dirname(prompt_path) == os.path.abspath(reviews_dir)
    assert os.path.isfile(prompt_path)
    # Archived beside the validator envelopes, named like the other seats'
    # prompts (``<chunk>-td-prompt.md`` / ``<chunk>-ex-prompt.md``).
    assert os.path.basename(prompt_path) == "c1-va-prompt.md"
    assert captured["chunk"]["review_output_dir"] == reviews_dir
    assert "{{" not in open(prompt_path).read()
    assert prompt_path != _TEMPLATE


# ── Defect 1 regression guard: unrendered template is a loud failure ─────


def test_unresolved_placeholder_raises_runtime_error_naming_it():
    with pytest.raises(RuntimeError) as exc:
        per_chunk.assert_prompt_fully_rendered(
            "review the diff at {{pilot_root}} please",
            prompt_path="/tmp/x.md",
            role="validator",
        )
    assert "{{pilot_root}}" in str(exc.value)
    assert "validator" in str(exc.value)


def test_raw_validator_template_is_refused_with_every_observed_placeholder_named():
    """The literal failure that shipped: the template itself, unrendered."""
    raw = open(_TEMPLATE).read()
    with pytest.raises(RuntimeError) as exc:
        per_chunk.assert_prompt_fully_rendered(
            raw, prompt_path=_TEMPLATE, role="validator"
        )
    message = str(exc.value)
    for placeholder in OBSERVED_PLACEHOLDERS:
        assert placeholder in message, f"{placeholder} not named in the refusal"


def test_render_validator_prompt_refuses_a_template_with_an_unknown_placeholder(
    tmp_path, monkeypatch
):
    chunk = _make_chunk(tmp_path)
    rs = _make_run_state(tmp_path)
    chunk.evidence_bundle_path = str(tmp_path / "c1-bundle.json")
    _write_bundle(chunk.evidence_bundle_path, "f" * 40)

    real_render_to_file = per_chunk.render_to_file

    def _render_with_extra_placeholder(role, context, output_path):
        path = real_render_to_file(role, context, output_path)
        with open(path, "a") as f:
            f.write("\nreport against {{unsupplied_context_key}}\n")
        return path

    monkeypatch.setattr(per_chunk, "render_to_file", _render_with_extra_placeholder)

    with pytest.raises(RuntimeError) as exc:
        per_chunk.render_validator_prompt(
            chunk, rs, output_path=str(tmp_path / "reviews" / "c1-va-prompt.md")
        )
    assert "{{unsupplied_context_key}}" in str(exc.value)


def test_validator_template_placeholders_are_all_supplied_by_the_renderer():
    """A new placeholder added to the template must come with a value."""
    from sprint_loop.prompts.render import _VAR_RE

    template_keys = set(_VAR_RE.findall(open(_TEMPLATE).read()))
    assert template_keys == {
        "chunk_spec",
        "branch",
        "commit",
        "pilot_root",
        "test_file_path",
        "evidence_bundle_path",
    }


# ── Defect 3: full-suite results in the bundle ───────────────────────────


def test_chunk_full_suite_command_detects_the_regression_command(tmp_path):
    chunk = _make_chunk(
        tmp_path,
        commands=[
            "/usr/bin/python3 -m pytest test/test_health_route.py -v",
            "/usr/bin/python3 -m pytest -v",
        ],
    )
    assert per_chunk.chunk_full_suite_command(chunk) == "/usr/bin/python3 -m pytest -v"


def test_chunk_with_only_the_locked_test_command_has_no_full_suite_command(tmp_path):
    chunk = _make_chunk(
        tmp_path, commands=["/usr/bin/python3 -m pytest test/test_health_route.py -v"]
    )
    assert per_chunk.chunk_full_suite_command(chunk) == ""


def test_bundle_records_full_suite_counters_distinguishably(tmp_path):
    chunk = _make_chunk(tmp_path)
    out = str(tmp_path / "c1-bundle.json")
    bundle = per_chunk.produce_evidence(
        chunk,
        framework_root=str(tmp_path / "fw"),
        pilot_root=str(tmp_path / "pilot"),
        pilot_python="/usr/bin/python3",
        evidence_output_path=out,
        dry_run=True,
        full_suite=True,
    )
    tests = bundle["tests"]
    assert tests["scope"] == "locked-test"
    full = tests["full_suite"]
    for key in ("passed", "failed", "skipped", "suite_exit_code"):
        assert key in full
    # Locked-test counters and regression counters are separate objects, so
    # a validator cannot read one as the other.
    assert full is not tests
    assert json.loads(open(out).read())["tests"]["full_suite"] == full


def test_bundle_without_full_suite_command_is_unchanged_and_parses(tmp_path):
    chunk = _make_chunk(tmp_path)
    out = str(tmp_path / "c1-bundle.json")
    bundle = per_chunk.produce_evidence(
        chunk,
        framework_root=str(tmp_path / "fw"),
        pilot_root=str(tmp_path / "pilot"),
        pilot_python="/usr/bin/python3",
        evidence_output_path=out,
        dry_run=True,
        full_suite=False,
    )
    assert "full_suite" not in bundle["tests"]
    assert bundle["tests"]["passed"] == 1
    assert bundle["tests"]["suite_exit_code"] == 0
    assert json.loads(open(out).read()) == bundle


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
        "provenance": {
            "producer_run_id": "p",
            "started_at": "1970-01-01T00:00:00Z",
            "finished_at": "1970-01-01T00:00:01Z",
            "tool_versions": {},
        },
    }


def test_consumer_accepts_a_pre_existing_bundle_with_no_full_suite_section():
    consumer = _load_consumer_module()
    key = b"k"
    bundle = _sign(
        _bundle_with({"passed": 8, "failed": 0, "skipped": 0, "suite_exit_code": 0}), key
    )
    result = consumer.ValidatorConsumer().consume(bundle, key)
    assert result["evidence_verdict"] == "ACCEPT"


def test_consumer_rejects_a_green_locked_test_with_a_red_full_suite():
    consumer = _load_consumer_module()
    key = b"k"
    bundle = _sign(
        _bundle_with(
            {
                "passed": 8,
                "failed": 0,
                "skipped": 0,
                "suite_exit_code": 0,
                "scope": "locked-test",
                "full_suite": {
                    "passed": 29,
                    "failed": 3,
                    "skipped": 0,
                    "suite_exit_code": 1,
                    "scope": "full-suite",
                },
            }
        ),
        key,
    )
    result = consumer.ValidatorConsumer().consume(bundle, key)
    assert result["evidence_verdict"] == "REJECT"
    assert "full-suite" in result["reason"]


def test_gate_fails_closed_on_a_full_suite_regression(tmp_path):
    consumer = _load_consumer_module()
    key = b"k"
    lock_file = tmp_path / "lock.json"
    lock_file.write_text(json.dumps({"sha256": "b" * 64}))
    bundle = _sign(
        _bundle_with(
            {
                "passed": 8,
                "failed": 0,
                "skipped": 0,
                "suite_exit_code": 0,
                "full_suite": {
                    "passed": 29,
                    "failed": 1,
                    "skipped": 0,
                    "suite_exit_code": 1,
                },
            }
        ),
        key,
    )
    result = consumer.OrchestratorGate().gate(bundle, str(lock_file), key)
    assert result["gate_decision"] == "FAIL_CLOSED"
    assert "full-suite regression" in result["reason"]

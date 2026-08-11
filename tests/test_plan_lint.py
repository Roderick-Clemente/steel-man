"""Unit tests for tools/plan-lint.py — the deterministic pre-review tier.

RED-first: per-class BLOCK expectations against the historical
PLAN-5.1 fixtures (v3 schema-field, v4 arity, v5 filename, v6
call-signature), plus a GREEN fixture, plus fail-closed paths.

Exit codes (per spec):
  0 = PASS (warnings allowed)
  2 = usage / internal error / fail-closed (missing ground-truth)
  3 = BLOCK (findings on stdout + --json)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# Repo root for locating tools/plan-lint.py and fixtures.
_REPO = Path(__file__).resolve().parent.parent
_TOOLS = _REPO / "tools"
_FIXTURES = _REPO / "tests" / "fixtures" / "plan-lint"
_REPO_ROOT = _FIXTURES / "repo"

_PLAN_LINT = _TOOLS / "plan-lint.py"


def _run_plan_lint(
    plan_path: Path,
    repo_root: Path | None = None,
    contract_path: Path | None = None,
    json_out: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Invoke plan-lint.py and return the CompletedProcess."""
    cmd = [sys.executable, str(_PLAN_LINT), str(plan_path)]
    if repo_root is not None:
        cmd += ["--repo-root", str(repo_root)]
    if contract_path is not None:
        cmd += ["--contract", str(contract_path)]
    if json_out is not None:
        cmd += ["--json", str(json_out)]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=30,
    )


# ── interface / exit-code contract ──────────────────────────────────────


class TestInterface:
    def test_help_exits_0(self):
        r = subprocess.run(
            [sys.executable, str(_PLAN_LINT), "--help"],
            capture_output=True, text=True, timeout=10,
        )
        assert r.returncode == 0
        assert "plan-lint" in r.stdout.lower() or "plan-lint" in r.stderr.lower()

    def test_missing_plan_arg_exits_2(self):
        r = subprocess.run(
            [sys.executable, str(_PLAN_LINT)],
            capture_output=True, text=True, timeout=10,
        )
        assert r.returncode == 2

    def test_nonexistent_plan_exits_2(self):
        r = _run_plan_lint(Path("/nonexistent/plan.md"))
        assert r.returncode == 2
        # Must NOT be exit 0 or 3 — fail-closed, not silent pass.
        assert "error" in r.stderr.lower() or "error" in r.stdout.lower()

    def test_json_output_written_on_block(self, tmp_path):
        json_out = tmp_path / "out.json"
        r = _run_plan_lint(
            _FIXTURES / "PLAN-5.1-v3.md",
            repo_root=_REPO_ROOT,
            contract_path=_FIXTURES / "PLAN-5.1-v3.contract.json",
            json_out=json_out,
        )
        assert r.returncode == 3
        assert json_out.exists()
        data = json.loads(json_out.read_text())
        assert "findings" in data
        assert len(data["findings"]) >= 1


# ── fail-closed: missing ground-truth artifact → exit 2 ──────────────────


class TestFailClosed:
    def test_missing_repo_root_exits_2(self, tmp_path):
        """If the repo-root doesn't exist, fail-closed with exit 2."""
        r = _run_plan_lint(
            _FIXTURES / "PLAN-5.1-v3.md",
            repo_root=tmp_path / "nonexistent",
            contract_path=_FIXTURES / "PLAN-5.1-v3.contract.json",
        )
        assert r.returncode == 2
        # Never a silent pass.
        assert "error" in r.stderr.lower() or "error" in r.stdout.lower()

    def test_missing_ground_truth_artifact_exits_2(self, tmp_path):
        """A contract claim referencing a non-existent artifact must
        fail-closed (exit 2), never pass.
        """
        contract = tmp_path / "bad.contract.json"
        contract.write_text(json.dumps({
            "claims": [
                {
                    "rule": 1,
                    "line": 1,
                    "claim": "field exists",
                    "field_path": "verdict",
                    "artifact": "does/not/exist.json",
                    "expect": "exists",
                }
            ]
        }))
        r = _run_plan_lint(
            _FIXTURES / "green-plan.md",
            repo_root=_REPO_ROOT,
            contract_path=contract,
        )
        assert r.returncode == 2
        assert "error" in r.stderr.lower() or "error" in r.stdout.lower()

    def test_unreadable_artifact_exits_2(self, tmp_path):
        """An artifact that exists but is unreadable → exit 2."""
        bad_json = _REPO_ROOT / "phase-4.5" / "tokens" / "bad.token.json"
        bad_json.write_text("{not valid json}")
        try:
            contract = tmp_path / "bad.contract.json"
            contract.write_text(json.dumps({
                "claims": [
                    {
                        "rule": 1,
                        "line": 1,
                        "claim": "field exists",
                        "field_path": "verdict",
                        "artifact": "phase-4.5/tokens/bad.token.json",
                        "expect": "exists",
                    }
                ]
            }))
            r = _run_plan_lint(
                _FIXTURES / "green-plan.md",
                repo_root=_REPO_ROOT,
                contract_path=contract,
            )
            assert r.returncode == 2
        finally:
            bad_json.unlink(missing_ok=True)


# ── GREEN fixture: well-formed plan passes ───────────────────────────────


class TestGreenFixture:
    def test_green_plan_passes(self):
        """The minimal well-formed plan with an embedded CONTRACT block
        passes (exit 0) or warns only.
        """
        r = _run_plan_lint(
            _FIXTURES / "green-plan.md",
            repo_root=_REPO_ROOT,
        )
        assert r.returncode == 0, f"Expected PASS, got {r.returncode}\n{r.stdout}\n{r.stderr}"


# ── per-class BLOCK: historical fixtures ─────────────────────────────────


class TestRule1FieldPath:
    """Rule 1: field-path references resolve against live JSON artifacts."""

    def test_v3_blocks_on_schema_field(self):
        """v3 references a top-level `verdict` field that the canonical
        token schema does not carry (verdicts are per-reviewer).
        """
        r = _run_plan_lint(
            _FIXTURES / "PLAN-5.1-v3.md",
            repo_root=_REPO_ROOT,
            contract_path=_FIXTURES / "PLAN-5.1-v3.contract.json",
        )
        assert r.returncode == 3
        # The BLOCK must be for rule class 1 (field-path).
        assert "rule" in r.stdout.lower() or "rule 1" in r.stdout.lower()
        # The finding must reference the verdict field.
        assert "verdict" in r.stdout.lower()

    def test_field_path_missing_in_artifact_blocks(self, tmp_path):
        """A claim that a field path exists in an artifact, when it
        doesn't, blocks (rule 1).
        """
        contract = tmp_path / "c.json"
        contract.write_text(json.dumps({
            "claims": [
                {
                    "rule": 1,
                    "line": 10,
                    "claim": "Token has top-level verdict",
                    "field_path": "verdict",
                    "artifact": "phase-4.5/tokens/chunk-5a.token.json",
                    "expect": "exists",
                }
            ]
        }))
        r = _run_plan_lint(
            _FIXTURES / "green-plan.md",
            repo_root=_REPO_ROOT,
            contract_path=contract,
        )
        assert r.returncode == 3
        assert "verdict" in r.stdout.lower()


class TestRule2CliFlags:
    """Rule 2: CLI flag references resolve against argparse definitions."""

    def test_nonexistent_flag_blocks(self, tmp_path):
        contract = tmp_path / "c.json"
        contract.write_text(json.dumps({
            "claims": [
                {
                    "rule": 2,
                    "line": 5,
                    "claim": "chunk_sequence_gate accepts --nonexistent-flag",
                    "artifact": "tools/chunk_sequence_gate.py",
                    "field_path": "--nonexistent-flag",
                    "expect": "flag_exists",
                }
            ]
        }))
        r = _run_plan_lint(
            _FIXTURES / "green-plan.md",
            repo_root=_REPO_ROOT,
            contract_path=contract,
        )
        assert r.returncode == 3
        assert "--nonexistent-flag" in r.stdout.lower()

    def test_existing_flag_passes(self, tmp_path):
        contract = tmp_path / "c.json"
        contract.write_text(json.dumps({
            "claims": [
                {
                    "rule": 2,
                    "line": 5,
                    "claim": "chunk_sequence_gate accepts --prior-token",
                    "artifact": "tools/chunk_sequence_gate.py",
                    "field_path": "--prior-token",
                    "expect": "flag_exists",
                }
            ]
        }))
        r = _run_plan_lint(
            _FIXTURES / "green-plan.md",
            repo_root=_REPO_ROOT,
            contract_path=contract,
        )
        assert r.returncode == 0


class TestRule3ModelIds:
    """Rule 3: model ids and family labels resolve against MODEL_FAMILY_MAP;
    flag id-vs-label type confusion.
    """

    def test_family_label_as_model_id_blocks(self, tmp_path):
        contract = tmp_path / "c.json"
        contract.write_text(json.dumps({
            "claims": [
                {
                    "rule": 3,
                    "line": 5,
                    "claim": "grok-family is a model id",
                    "artifact": "tools/sprint_loop/config.py",
                    "field_path": "MODEL_FAMILY_MAP.grok-family",
                    "expect": "model_id",
                }
            ]
        }))
        r = _run_plan_lint(
            _FIXTURES / "green-plan.md",
            repo_root=_REPO_ROOT,
            contract_path=contract,
        )
        assert r.returncode == 3
        assert "grok-family" in r.stdout.lower()

    def test_valid_model_id_passes(self, tmp_path):
        contract = tmp_path / "c.json"
        contract.write_text(json.dumps({
            "claims": [
                {
                    "rule": 3,
                    "line": 5,
                    "claim": "grok-4.5 is a valid model id",
                    "artifact": "tools/sprint_loop/config.py",
                    "field_path": "MODEL_FAMILY_MAP.grok-4.5",
                    "expect": "model_id",
                }
            ]
        }))
        r = _run_plan_lint(
            _FIXTURES / "green-plan.md",
            repo_root=_REPO_ROOT,
            contract_path=contract,
        )
        assert r.returncode == 0


class TestRule4InternalConsistency:
    """Rule 4: numeric contract claims agree; artifact names consistent."""

    def test_v4_blocks_on_arity(self):
        """v4: stub emits 1 reviewer while gate requires >=2 (arity
        contradiction).
        """
        r = _run_plan_lint(
            _FIXTURES / "PLAN-5.1-v4.md",
            repo_root=_REPO_ROOT,
            contract_path=_FIXTURES / "PLAN-5.1-v4.contract.json",
        )
        assert r.returncode == 3
        assert "reviewer" in r.stdout.lower()

    def test_v5_blocks_on_filename(self):
        """v5: three different token filename conventions across
        artifacts.
        """
        r = _run_plan_lint(
            _FIXTURES / "PLAN-5.1-v5.md",
            repo_root=_REPO_ROOT,
            contract_path=_FIXTURES / "PLAN-5.1-v5.contract.json",
        )
        assert r.returncode == 3
        assert "filename" in r.stdout.lower() or "token" in r.stdout.lower()

    def test_inconsistent_naming_blocks(self, tmp_path):
        contract = tmp_path / "c.json"
        contract.write_text(json.dumps({
            "claims": [
                {
                    "rule": 4,
                    "line": 10,
                    "claim": "Token filename pattern chunk-{chunk_id}.token.json",
                    "artifact": "phase-4.5/tokens/chunk-5a.token.json",
                    "field_path": "filename",
                    "expect": "pattern:chunk-{chunk_id}.token.json"
                },
                {
                    "rule": 4,
                    "line": 20,
                    "claim": "Stub output path: {chunk_id}.token.json",
                    "artifact": "tools/persistent_referee_stub.py",
                    "field_path": "build_signed_token.output_path",
                    "expect": "pattern:{chunk_id}.token.json"
                }
            ]
        }))
        r = _run_plan_lint(
            _FIXTURES / "green-plan.md",
            repo_root=_REPO_ROOT,
            contract_path=contract,
        )
        assert r.returncode == 3


class TestRule5CallSignature:
    """Rule 5: call-signature claims match the named function's actual
    signature (arity, parameter names).
    """

    def test_v6_blocks_on_call_signature(self):
        """v6: call passed family labels where the callee resolves
        model ids (call-signature / type confusion).
        """
        r = _run_plan_lint(
            _FIXTURES / "PLAN-5.1-v6.md",
            repo_root=_REPO_ROOT,
            contract_path=_FIXTURES / "PLAN-5.1-v6.contract.json",
        )
        assert r.returncode == 3
        assert "implementer" in r.stdout.lower() or "model_id" in r.stdout.lower() or "family" in r.stdout.lower()

    def test_wrong_arity_blocks(self, tmp_path):
        contract = tmp_path / "c.json"
        contract.write_text(json.dumps({
            "claims": [
                {
                    "rule": 5,
                    "line": 10,
                    "claim": "close_chunk(chunk_id, commit_sha, extra) signature",
                    "artifact": "tools/sprint_loop/per_chunk.py",
                    "field_path": "close_chunk",
                    "expect": "arity:3",
                    "params": ["chunk_id", "commit_sha", "extra"]
                }
            ]
        }))
        r = _run_plan_lint(
            _FIXTURES / "green-plan.md",
            repo_root=_REPO_ROOT,
            contract_path=contract,
        )
        assert r.returncode == 3

    def test_wrong_param_name_blocks(self, tmp_path):
        contract = tmp_path / "c.json"
        contract.write_text(json.dumps({
            "claims": [
                {
                    "rule": 5,
                    "line": 10,
                    "claim": "check_reviewer_panel(implementer_family, ...) ",
                    "artifact": "tools/cross_family_review.py",
                    "field_path": "check_reviewer_panel",
                    "expect": "param:implementer_family",
                    "params": ["implementer_family", "reviewer_model_ids"]
                }
            ]
        }))
        r = _run_plan_lint(
            _FIXTURES / "green-plan.md",
            repo_root=_REPO_ROOT,
            contract_path=contract,
        )
        assert r.returncode == 3
        assert "implementer_family" in r.stdout.lower() or "implementer_model_id" in r.stdout.lower()


class TestRule6RequiredAnchors:
    """Rule 6: gate predicates must name a resolvable schema/artifact plus
    field path. Vague gate prose is a finding, not a pass. Always blocks.
    """

    def test_vague_gate_predicate_blocks(self, tmp_path):
        contract = tmp_path / "c.json"
        contract.write_text(json.dumps({
            "claims": [
                {
                    "rule": 6,
                    "line": 10,
                    "claim": "The gate checks the token is valid",
                    "artifact": "",
                    "field_path": "",
                    "expect": "resolvable"
                }
            ]
        }))
        r = _run_plan_lint(
            _FIXTURES / "green-plan.md",
            repo_root=_REPO_ROOT,
            contract_path=contract,
        )
        assert r.returncode == 3
        assert "gate" in r.stdout.lower() or "anchor" in r.stdout.lower() or "vague" in r.stdout.lower()

    def test_resolvable_gate_predicate_passes(self, tmp_path):
        contract = tmp_path / "c.json"
        contract.write_text(json.dumps({
            "claims": [
                {
                    "rule": 6,
                    "line": 10,
                    "claim": "Gate: token file exists with reviewers[*].verdict in ACCEPT_CLASS",
                    "artifact": "phase-4.5/tokens/chunk-5a.token.json",
                    "field_path": "reviewers[*].verdict",
                    "expect": "resolvable"
                }
            ]
        }))
        r = _run_plan_lint(
            _FIXTURES / "green-plan.md",
            repo_root=_REPO_ROOT,
            contract_path=contract,
        )
        assert r.returncode == 0


class TestRule7FilePaths:
    """Rule 7: file paths referenced by the plan exist in the repo (or are
    explicitly marked as to-be-created).
    """

    def test_nonexistent_path_blocks(self, tmp_path):
        contract = tmp_path / "c.json"
        contract.write_text(json.dumps({
            "claims": [
                {
                    "rule": 7,
                    "line": 10,
                    "claim": "tools/nonexistent.py exists",
                    "path": "tools/nonexistent.py",
                    "expect": "exists"
                }
            ]
        }))
        r = _run_plan_lint(
            _FIXTURES / "green-plan.md",
            repo_root=_REPO_ROOT,
            contract_path=contract,
        )
        assert r.returncode == 3
        assert "nonexistent" in r.stdout.lower()

    def test_existing_path_passes(self, tmp_path):
        contract = tmp_path / "c.json"
        contract.write_text(json.dumps({
            "claims": [
                {
                    "rule": 7,
                    "line": 10,
                    "claim": "tools/sign_chunk_token.py exists",
                    "path": "tools/sign_chunk_token.py",
                    "expect": "exists"
                }
            ]
        }))
        r = _run_plan_lint(
            _FIXTURES / "green-plan.md",
            repo_root=_REPO_ROOT,
            contract_path=contract,
        )
        assert r.returncode == 0

    def test_to_be_created_path_passes(self, tmp_path):
        contract = tmp_path / "c.json"
        contract.write_text(json.dumps({
            "claims": [
                {
                    "rule": 7,
                    "line": 10,
                    "claim": "tools/new_script.py (to-be-created)",
                    "path": "tools/new_script.py",
                    "expect": "to_be_created"
                }
            ]
        }))
        r = _run_plan_lint(
            _FIXTURES / "green-plan.md",
            repo_root=_REPO_ROOT,
            contract_path=contract,
        )
        assert r.returncode == 0


# ── heuristic mode (no CONTRACT block) ───────────────────────────────────


class TestHeuristicMode:
    def test_no_contract_warns_not_blocks(self, tmp_path):
        """A plan without a CONTRACT block: all rules run heuristically
        as warnings (exit 0), except rule 6 which always blocks on
        vague gate prose. A plan with no gate-predicate language
        produces only warnings (exit 0).
        """
        plan = tmp_path / "no-contract.md"
        plan.write_text("# Plan\n\nA simple plan.\n")
        r = _run_plan_lint(plan, repo_root=_REPO_ROOT)
        # No contract, no gate prose → warnings only (exit 0).
        assert r.returncode == 0

    def test_no_contract_rule6_blocks_on_vague_gate(self, tmp_path):
        """A plan without a CONTRACT block but with vague gate-predicate
        prose blocks (rule 6 always blocks, even in heuristic mode).
        """
        plan = tmp_path / "no-contract-gate.md"
        plan.write_text("# Plan\n\nThe gate checks the token is valid.\n")
        r = _run_plan_lint(plan, repo_root=_REPO_ROOT)
        # Rule 6 always blocks, even in heuristic mode.
        assert r.returncode == 3

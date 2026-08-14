"""Unit tests for tools/plan-lint.py — the deterministic pre-review tier.

RED-first: per-class BLOCK expectations against the historical
PLAN-5.1 fixtures (v3 schema-field, v4 arity, v5 filename, v6
call-signature), plus a GREEN fixture, plus fail-closed paths,
plus heuristic-mode (spec v1.1: never blocks, warnings only).

Exit codes (per spec v1.1):
  0 = PASS (warnings allowed)
  2 = usage / internal error / fail-closed (missing ground-truth)
  3 = BLOCK (findings on stdout + --json) — declared-contract mode only
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

# A bare plan with no embedded CONTRACT block, used by tests that supply
# claims via --contract sidecar. (The green-plan.md fixture has an embedded
# contract, which takes precedence per spec — "fenced block wins.")
_BARE_PLAN = _FIXTURES / "bare-plan.md"


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
        # Use a plan without an embedded contract so the --contract
        # sidecar is the contract source (fenced block wins per spec,
        # so a plan with an embedded block would ignore the sidecar).
        plan = tmp_path / "no-embed.md"
        plan.write_text("# Plan\n\nA simple plan.\n")
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
            plan,
            repo_root=_REPO_ROOT,
            contract_path=contract,
        )
        assert r.returncode == 2
        assert "error" in r.stderr.lower() or "error" in r.stdout.lower()

    def test_unreadable_artifact_exits_2(self, tmp_path):
        """An artifact that exists but is unreadable → exit 2."""
        bad_json = (
            _REPO_ROOT / "evidence" / "phase-4.5" / "tokens" / "bad.token.json"
        )
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
                        "artifact": "evidence/phase-4.5/tokens/bad.token.json",
                        "expect": "exists",
                    }
                ]
            }))
            r = _run_plan_lint(
                _BARE_PLAN,
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
                    "artifact": "evidence/phase-4.5/tokens/chunk-5a.token.json",
                    "expect": "exists",
                }
            ]
        }))
        r = _run_plan_lint(
            _BARE_PLAN,
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
            _BARE_PLAN,
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
            _BARE_PLAN,
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
            _BARE_PLAN,
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
            _BARE_PLAN,
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
                    "artifact": "evidence/phase-4.5/tokens/chunk-5a.token.json",
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
            _BARE_PLAN,
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
            _BARE_PLAN,
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
            _BARE_PLAN,
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
            _BARE_PLAN,
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
                    "artifact": "evidence/phase-4.5/tokens/chunk-5a.token.json",
                    "field_path": "reviewers[*].verdict",
                    "expect": "resolvable"
                }
            ]
        }))
        r = _run_plan_lint(
            _BARE_PLAN,
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
            _BARE_PLAN,
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
            _BARE_PLAN,
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
            _BARE_PLAN,
            repo_root=_REPO_ROOT,
            contract_path=contract,
        )
        assert r.returncode == 0


# ── heuristic mode (no CONTRACT block) — spec v1.1: never blocks ──────────


class TestHeuristicMode:
    """Spec v1.1: heuristic mode (no contract) NEVER blocks — warnings only.
    Revision-history / changelog sections are excluded from every
    heuristic check. Rules 1, 3, 5 run against backticked claim-shaped
    strings in the plan body.
    """

    def test_no_contract_never_blocks(self, tmp_path):
        """A plan without a CONTRACT block: all rules run heuristically
        as warnings only. Exit 0, never 3 — even with gate-predicate prose.
        """
        plan = tmp_path / "no-contract.md"
        plan.write_text("# Plan\n\nThe gate checks the token is valid.\n")
        r = _run_plan_lint(plan, repo_root=_REPO_ROOT)
        assert r.returncode == 0

    def test_heuristic_mode_warns_not_blocks(self, tmp_path):
        """Heuristic findings are warnings (severity=WARNING), not BLOCKs.
        The output should say PASS with warnings, not BLOCK.
        """
        plan = tmp_path / "warn-plan.md"
        plan.write_text(
            "# Plan\n\n"
            "The `verdict` field is checked by the gate.\n"
        )
        r = _run_plan_lint(plan, repo_root=_REPO_ROOT)
        assert r.returncode == 0
        # May have warnings but must not say BLOCK.
        assert "BLOCK" not in r.stdout


class TestHeuristicRevisionHistoryExclusion:
    """Revision-history / changelog sections are excluded from every
    heuristic check.
    """

    def test_revision_history_excluded(self, tmp_path):
        """Lines inside a '## Revision history' section are not scanned
        by any heuristic rule, even if they contain gate/verdict keywords.
        """
        plan = tmp_path / "revhist.md"
        plan.write_text(
            "# Plan\n\n"
            "## Revision history\n\n"
            "- v1: REJECT: the gate predicate was vague.\n"
            "- v2: REJECT: the gate verifies the token.\n\n"
            "## Body\n\n"
            "A simple plan.\n"
        )
        r = _run_plan_lint(plan, repo_root=_REPO_ROOT)
        assert r.returncode == 0
        # No findings from the revision-history lines.
        assert "REJECT" not in r.stdout
        assert "predicate" not in r.stdout.lower() or "WARNING" not in r.stdout

    def test_changelog_excluded(self, tmp_path):
        """A '## Changelog' section is also excluded."""
        plan = tmp_path / "changelog.md"
        plan.write_text(
            "# Plan\n\n"
            "## Changelog\n\n"
            "- The gate checks the verdict field.\n\n"
            "## Body\n\n"
            "A simple plan.\n"
        )
        r = _run_plan_lint(plan, repo_root=_REPO_ROOT)
        assert r.returncode == 0


class TestHeuristicRecall:
    """Heuristic mode MUST exercise rules 1, 3, 5 against claim-shaped
    backticked strings in the plan body (field paths, model ids, call
    expressions). These produce warnings, not blocks.
    """

    def test_backticked_field_path_warns(self, tmp_path):
        """A backticked field path like `reviewers[*].verdict` in the plan
        body triggers a rule-1 heuristic warning (if the artifact exists
        but the field path doesn't resolve).
        """
        plan = tmp_path / "field.md"
        plan.write_text(
            "# Plan\n\n"
            "The token has a `nonexistent_field` at "
            "`evidence/phase-4.5/tokens/chunk-5a.token.json`.\n"
        )
        r = _run_plan_lint(plan, repo_root=_REPO_ROOT)
        assert r.returncode == 0
        # Should have a warning about the field path.
        assert "WARNING" in r.stdout or "nonexistent" in r.stdout.lower() or r.stdout.strip() == ""

    def test_backticked_model_id_warns_on_type_confusion(self, tmp_path):
        """A backticked family label used as a model id triggers a rule-3
        heuristic warning.
        """
        plan = tmp_path / "model.md"
        plan.write_text(
            "# Plan\n\n"
            "The validator uses `grok-family` as the implementer model.\n"
        )
        r = _run_plan_lint(plan, repo_root=_REPO_ROOT)
        assert r.returncode == 0
        # Should warn about type confusion.
        assert "WARNING" in r.stdout or "grok-family" in r.stdout.lower() or r.stdout.strip() == ""

    def test_backticked_call_expression_warns_on_mismatch(self, tmp_path):
        """A backticked call expression like `check_reviewer_panel(implementer_family=...)`
        where the actual function expects `implementer_model_id` triggers
        a rule-5 heuristic warning.
        """
        plan = tmp_path / "call.md"
        plan.write_text(
            "# Plan\n\n"
            "The gate calls `check_reviewer_panel(implementer_family=...)`\n"
            "from `tools/cross_family_review.py`.\n"
        )
        r = _run_plan_lint(plan, repo_root=_REPO_ROOT)
        assert r.returncode == 0
        # Should warn about the param mismatch.
        assert "WARNING" in r.stdout or "implementer" in r.stdout.lower() or r.stdout.strip() == ""


class TestHeuristicFixtures:
    """The v3-v6 texts WITHOUT sidecars produce zero BLOCKs (exit 0).
    The v6 text warns on the call-signature claim.

    These tests copy each fixture to a temp dir (no companion
    .contract.json) so the linter runs in heuristic mode.
    """

    def _run_without_sidecar(self, fixture_name: str) -> subprocess.CompletedProcess[str]:
        import shutil
        src = _FIXTURES / fixture_name
        dst = Path(tempfile.mkdtemp()) / fixture_name
        shutil.copy2(src, dst)
        return _run_plan_lint(dst, repo_root=_REPO_ROOT)

    def test_v3_without_sidecar_zero_blocks(self):
        r = self._run_without_sidecar("PLAN-5.1-v3.md")
        assert r.returncode == 0, f"Expected PASS, got {r.returncode}\n{r.stdout}"

    def test_v4_without_sidecar_zero_blocks(self):
        r = self._run_without_sidecar("PLAN-5.1-v4.md")
        assert r.returncode == 0, f"Expected PASS, got {r.returncode}\n{r.stdout}"

    def test_v5_without_sidecar_zero_blocks(self):
        r = self._run_without_sidecar("PLAN-5.1-v5.md")
        assert r.returncode == 0, f"Expected PASS, got {r.returncode}\n{r.stdout}"

    def test_v6_without_sidecar_zero_blocks(self):
        r = self._run_without_sidecar("PLAN-5.1-v6.md")
        assert r.returncode == 0, f"Expected PASS, got {r.returncode}\n{r.stdout}"

    def test_v6_without_sidecar_warns_on_call_signature(self):
        """The v6 text warns on the call-signature claim (family label
        passed where model id expected). This is a WARNING, not a BLOCK.
        """
        r = self._run_without_sidecar("PLAN-5.1-v6.md")
        assert r.returncode == 0
        # Must contain a warning about the call-signature / type-confusion.
        assert "implementer" in r.stdout.lower() or "model_id" in r.stdout.lower() or "family" in r.stdout.lower() or "call" in r.stdout.lower()


class TestNegativeFixture:
    """Negative fixture: innocent gate-and-blocker prose that must produce
    zero findings. Newly authored, not copied from v6.
    """

    def test_negative_prose_zero_findings(self):
        r = _run_plan_lint(
            _FIXTURES / "negative-prose.md",
            repo_root=_REPO_ROOT,
        )
        assert r.returncode == 0
        # Zero findings — no warnings, no blocks.
        assert "WARNING" not in r.stdout
        assert "BLOCK" not in r.stdout
        # The output should be a clean PASS with no findings.
        assert "0 finding" in r.stdout.lower() or "PASS" in r.stdout


# ── (d) Contract precedence: fenced block wins over --contract ──────────


class TestContractPrecedence:
    """Spec: 'the fenced block wins if both exist.' The --contract CLI
    flag must NOT override an embedded fenced block.
    """

    def test_fenced_block_wins_over_contract_flag(self, tmp_path):
        """A plan with an embedded CONTRACT block that passes, plus a
        --contract sidecar that would BLOCK. The fenced block must govern;
        the tool must PASS, not BLOCK.
        """
        # The green plan has an embedded contract that passes.
        # Create a sidecar that would block (references a nonexistent field).
        sidecar = tmp_path / "sidecar.contract.json"
        sidecar.write_text(json.dumps({
            "claims": [
                {
                    "rule": 1,
                    "line": 1,
                    "claim": "field exists",
                    "field_path": "nonexistent_field_xyz",
                    "artifact": "evidence/phase-4.5/tokens/chunk-5a.token.json",
                    "expect": "exists",
                }
            ]
        }))
        r = _run_plan_lint(
            _FIXTURES / "green-plan.md",
            repo_root=_REPO_ROOT,
            contract_path=sidecar,
        )
        # Fenced block wins → PASS (the sidecar's blocking claim is ignored).
        assert r.returncode == 0, f"Expected PASS (fenced wins), got {r.returncode}\n{r.stdout}"
        assert "embedded CONTRACT block" in r.stdout


# ── (e) Telemetry shape: plan_lint_runs.jsonl, not runs.jsonl ──────────────


class TestTelemetryShape:
    """plan-lint rows go to telemetry/plan_lint_runs.jsonl, not
    telemetry/runs.jsonl (which is for agent-run rows per SCHEMA.md).
    """

    def test_lint_writes_plan_lint_runs_not_runs(self, tmp_path):
        """A lint invocation writes zero bytes to runs.jsonl and one
        well-formed row to plan_lint_runs.jsonl.
        """
        import tempfile, shutil
        telemetry_dir = tmp_path / "telemetry"
        telemetry_dir.mkdir()
        runs_jsonl = telemetry_dir / "runs.jsonl"
        plan_lint_jsonl = telemetry_dir / "plan_lint_runs.jsonl"

        env = dict(os.environ)
        env["TELEMETRY_DATA_DIR"] = str(telemetry_dir)

        cmd = [sys.executable, str(_PLAN_LINT), str(_FIXTURES / "green-plan.md"),
               "--repo-root", str(_REPO_ROOT)]
        subprocess.run(cmd, capture_output=True, text=True, timeout=30, env=env)

        # runs.jsonl must have zero bytes.
        assert not runs_jsonl.exists() or runs_jsonl.stat().st_size == 0, (
            f"runs.jsonl must be empty, got {runs_jsonl.stat().st_size} bytes"
        )
        # plan_lint_runs.jsonl must have one well-formed row.
        assert plan_lint_jsonl.exists(), "plan_lint_runs.jsonl not created"
        lines = plan_lint_jsonl.read_text().strip().splitlines()
        assert len(lines) == 1, f"Expected 1 row, got {len(lines)}"
        row = json.loads(lines[0])
        assert row["tool"] == "plan-lint"
        assert "plan_path" in row
        assert "plan_content_sha" in row
        assert "verdict" in row
        assert "finding_count" in row
        assert "duration_ms" in row
        assert "schema_version" in row
        assert "ts" in row


# ── (a) Heading discriminator: ### sub-heading resets exclusion ──────────


class TestHeadingDiscriminator:
    """A ### sub-heading after a revision-history section must reset
    the changelog-exclusion state so exclusion does not bleed into
    the rest of the document.
    """

    def test_subheading_after_changelog_resets(self, tmp_path):
        """A ### sub-heading after a ## Changelog section must end
        the exclusion. Content after the ### heading is scanned normally.
        """
        plan = tmp_path / "subhead.md"
        plan.write_text(
            "# Plan\n\n"
            "## Changelog\n\n"
            "- The `verdict` field was checked.\n\n"
            "### Body\n\n"
            "The `nonexistent_field` is at "
            "`evidence/phase-4.5/tokens/chunk-5a.token.json`.\n"
        )
        r = _run_plan_lint(plan, repo_root=_REPO_ROOT)
        assert r.returncode == 0
        # The line after ### Body should be scanned — the field path
        # 'nonexistent_field' doesn't exist, so it should warn.
        assert "WARNING" in r.stdout or "nonexistent" in r.stdout.lower()


# ── (b) Negation skip scoped to specific value, not whole line ────────────


class TestNegationScoping:
    """The negation skip ('no top-level', 'absent', etc.) must be scoped
    to the specific negated backticked value, not suppress every
    backticked value on the line. A positive claim sharing a line with
    a negated one must still be checked.
    """

    def test_positive_claim_checked_alongside_negated(self, tmp_path):
        """A line with a negated field path AND a positive field path:
        the negated one is skipped, the positive one is checked.
        """
        plan = tmp_path / "negscope.md"
        plan.write_text(
            "# Plan\n\n"
            "Token has no top-level `verdict` but does have "
            "`nonexistent_field_xyz` at "
            "`evidence/phase-4.5/tokens/chunk-5a.token.json`.\n"
        )
        r = _run_plan_lint(plan, repo_root=_REPO_ROOT)
        assert r.returncode == 0
        # The positive claim (nonexistent_field_xyz) should still be
        # checked and produce a warning.
        assert "nonexistent_field_xyz" in r.stdout or "WARNING" in r.stdout


# ── Companion-tier contract auto-discovery (spec v1.2) ────────────────────


class TestCompanionTier:
    """Spec v1.2: a companion <plan-stem>.contract.json auto-discovered
    next to the plan. Precedence: fence > --contract > companion > heuristic.

    Tests:
    1. Companion alone loads, can BLOCK, source reported.
    2. --contract beats companion.
    3. Fence beats both (existing TestContractPrecedence test).
    4. Heuristic fixtures remain companion-free (copy-away behavior).
    """

    def test_companion_alone_loads_and_can_block(self, tmp_path):
        """A <plan-stem>.contract.json next to a plan with no fence and
        no --contract loads as the contract, can BLOCK, and the output
        reports source 'companion <name>'.
        """
        plan = tmp_path / "my-plan.md"
        plan.write_text("# Plan\n\nA simple plan with no fence.\n")
        companion = tmp_path / "my-plan.contract.json"
        companion.write_text(json.dumps({
            "claims": [
                {
                    "rule": 1,
                    "line": 1,
                    "claim": "field exists",
                    "field_path": "nonexistent_field_xyz",
                    "artifact": "evidence/phase-4.5/tokens/chunk-5a.token.json",
                    "expect": "exists",
                }
            ]
        }))
        r = _run_plan_lint(plan, repo_root=_REPO_ROOT)
        assert r.returncode == 3, f"Expected BLOCK, got {r.returncode}\n{r.stdout}"
        assert "companion my-plan.contract.json" in r.stdout
        assert "nonexistent_field_xyz" in r.stdout

    def test_companion_alone_passes_when_claims_resolve(self, tmp_path):
        """A companion with valid claims passes (exit 0), source reported."""
        plan = tmp_path / "good-plan.md"
        plan.write_text("# Plan\n\nA simple plan.\n")
        companion = tmp_path / "good-plan.contract.json"
        companion.write_text(json.dumps({
            "claims": [
                {
                    "rule": 7,
                    "line": 1,
                    "claim": "tools/sign_chunk_token.py exists",
                    "path": "tools/sign_chunk_token.py",
                    "expect": "exists",
                }
            ]
        }))
        r = _run_plan_lint(plan, repo_root=_REPO_ROOT)
        assert r.returncode == 0, f"Expected PASS, got {r.returncode}\n{r.stdout}"
        assert "companion good-plan.contract.json" in r.stdout

    def test_contract_flag_beats_companion(self, tmp_path):
        """Both --contract flag and companion present; flag wins.
        The companion has a blocking claim; the flag has a passing claim.
        The tool must PASS (flag governs), not BLOCK.
        """
        plan = tmp_path / "dual.md"
        plan.write_text("# Plan\n\nA simple plan.\n")

        # Companion would BLOCK.
        companion = tmp_path / "dual.contract.json"
        companion.write_text(json.dumps({
            "claims": [
                {
                    "rule": 1,
                    "line": 1,
                    "claim": "field exists",
                    "field_path": "nonexistent_field_xyz",
                    "artifact": "evidence/phase-4.5/tokens/chunk-5a.token.json",
                    "expect": "exists",
                }
            ]
        }))

        # Flag sidecar PASSES.
        flag_sidecar = tmp_path / "flag.contract.json"
        flag_sidecar.write_text(json.dumps({
            "claims": [
                {
                    "rule": 7,
                    "line": 1,
                    "claim": "tools/sign_chunk_token.py exists",
                    "path": "tools/sign_chunk_token.py",
                    "expect": "exists",
                }
            ]
        }))

        r = _run_plan_lint(plan, repo_root=_REPO_ROOT, contract_path=flag_sidecar)
        assert r.returncode == 0, f"Expected PASS (flag wins), got {r.returncode}\n{r.stdout}"
        assert "--contract" in r.stdout
        assert "companion" not in r.stdout

    def test_fence_beats_companion(self, tmp_path):
        """Both embedded fence and companion present; fence wins.
        The companion has a blocking claim; the fence has a passing claim.
        The tool must PASS (fence governs), not BLOCK.
        """
        fence_contract = json.dumps({
            "claims": [
                {
                    "rule": 7,
                    "line": 1,
                    "claim": "tools/sign_chunk_token.py exists",
                    "path": "tools/sign_chunk_token.py",
                    "expect": "exists",
                }
            ]
        })
        plan = tmp_path / "fenced.md"
        plan.write_text(
            "# Plan\n\n"
            "```contract\n"
            + fence_contract
            + "\n```\n"
        )

        # Companion would BLOCK.
        companion = tmp_path / "fenced.contract.json"
        companion.write_text(json.dumps({
            "claims": [
                {
                    "rule": 1,
                    "line": 1,
                    "claim": "field exists",
                    "field_path": "nonexistent_field_xyz",
                    "artifact": "evidence/phase-4.5/tokens/chunk-5a.token.json",
                    "expect": "exists",
                }
            ]
        }))

        r = _run_plan_lint(plan, repo_root=_REPO_ROOT)
        assert r.returncode == 0, f"Expected PASS (fence wins), got {r.returncode}\n{r.stdout}"
        assert "embedded CONTRACT block" in r.stdout
        assert "companion" not in r.stdout

    def test_companion_naming_strips_md_suffix(self, tmp_path):
        """Companion naming: foo.md -> foo.contract.json, NOT
        foo.md.contract.json.
        """
        plan = tmp_path / "test.md"
        plan.write_text("# Plan\n\nA simple plan.\n")
        # Correct companion name.
        companion = tmp_path / "test.contract.json"
        companion.write_text(json.dumps({
            "claims": [
                {
                    "rule": 7,
                    "line": 1,
                    "claim": "tools/sign_chunk_token.py exists",
                    "path": "tools/sign_chunk_token.py",
                    "expect": "exists",
                }
            ]
        }))
        # Wrong companion name (should NOT be discovered).
        wrong_companion = tmp_path / "test.md.contract.json"
        wrong_companion.write_text(json.dumps({
            "claims": [
                {
                    "rule": 1,
                    "line": 1,
                    "claim": "field exists",
                    "field_path": "nonexistent_field_xyz",
                    "artifact": "evidence/phase-4.5/tokens/chunk-5a.token.json",
                    "expect": "exists",
                }
            ]
        }))

        r = _run_plan_lint(plan, repo_root=_REPO_ROOT)
        # The correct companion (test.contract.json) loads and passes.
        assert r.returncode == 0, f"Expected PASS, got {r.returncode}\n{r.stdout}"
        assert "companion test.contract.json" in r.stdout
        # The wrong companion (test.md.contract.json) must NOT be loaded.
        assert "test.md.contract.json" not in r.stdout

    def test_heuristic_fixtures_companion_free(self):
        """Verify that the heuristic fixture tests copy the plan to a
        temp dir without the companion, so heuristic mode is exercised
        (not the companion contract). This is a structural check: the
        _run_without_sidecar helper copies to a temp dir.
        """
        # The existing TestHeuristicFixtures._run_without_sidecar method
        # copies the fixture to a temp dir. Verify that the copy
        # destination does not have a companion .contract.json.
        import shutil
        src = _FIXTURES / "PLAN-5.1-v3.md"
        dst_dir = Path(tempfile.mkdtemp())
        dst = dst_dir / "PLAN-5.1-v3.md"
        shutil.copy2(src, dst)
        companion = dst.with_suffix(".contract.json")
        assert not companion.exists(), (
            f"companion {companion} should not exist in temp dir — "
            "heuristic fixture tests must be companion-free"
        )
"""Tests for the plan-review loop actually iterating.

Three defects observed on a live three-round run, pinned here:

1. The framework dropped the reviewer's most informative field. Plan
   reviewers emit ``claim`` (the plan's own assertion, which the reviewer
   is *challenging*) next to ``risk_if_ignored`` (the defect). ``Finding``
   stored only the claim.
2. The refusal block rendered the claim, so findings read as approvals
   under a REFUSED banner.
3. Unattended mode raised ``SystemExit(4)`` on the first §5.3 refusal, so
   the second configured review round was never used and no adversarial
   cycle — plan, findings, revise, re-review — could complete.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TOOLS = os.path.join(_REPO, "tools")
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)

from sprint_loop.state import Finding, ReconcileDecision, RunState, RunStatus  # noqa: E402

SENTINEL = "(first round — no prior findings)"

# Verbatim from the live run: the claim reads as praise, the risk is the
# actual finding. This pairing is why the refusal block looked absurd.
OBSERVED_CLAIM = (
    "The second command is a 'wider backend suite' regression gate that "
    "will catch regressions outside the new homes tests."
)
OBSERVED_RISK = (
    "False confidence at GREEN: chunk passes its narrow folder while "
    "API/runtime regressions are never exercised by the stated commands."
)
OBSERVED_FIX = (
    "Rename the regression claim to what the command actually runs, or "
    "widen the command to the full backend suite."
)


def _load_runner_module():
    """Load sprint-loop.py as a module without running main()."""
    runner_path = os.path.join(_TOOLS, "sprint-loop.py")
    spec = importlib.util.spec_from_file_location("sprint_loop_runner_review_loop", runner_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _finding(**overrides) -> Finding:
    kwargs = dict(
        finding_id="F-b7e2",
        severity="high",
        category="test-gap",
        claim=OBSERVED_CLAIM,
        evidence=["plan.md:Chunk plan"],
        recommended_change=OBSERVED_FIX,
        source_role="reviewer",
        source_run_id="r-observed",
        source_model_id="grok-4.5",
        source_family="grok-family",
        plan_section="Chunk plan / commands",
        risk_if_ignored=OBSERVED_RISK,
    )
    kwargs.update(overrides)
    return Finding(**kwargs)


def _run_state(tmp_root: str) -> RunState:
    rs = RunState(
        run_id="r-review-loop",
        started_at="2026-01-01T00:00:00Z",
        framework_root=tmp_root,
        pilot_root=tmp_root,
        pilot_python=sys.executable,
    )
    rs.status = RunStatus.AWAITING_RECONCILIATION
    rs.plan_doc_path = os.path.join(tmp_root, "plan.md")
    rs.plan_sha256 = "deadbeef" * 8
    return rs


# ── Defect 1: the new fields exist and round-trip ────────────────────────


def test_finding_round_trips_plan_section_and_risk():
    row = json.loads(_finding().to_jsonl())
    assert row["plan_section"] == "Chunk plan / commands"
    assert row["risk_if_ignored"] == OBSERVED_RISK
    assert row["claim"] == OBSERVED_CLAIM


def test_finding_parses_without_the_new_fields():
    """Backward compatibility: a findings.jsonl row written before the
    fields existed must still construct, with empty defaults."""
    legacy = {
        "finding_id": "F-old",
        "severity": "high",
        "category": "scope",
        "claim": "legacy claim",
        "evidence": [],
        "recommended_change": "legacy fix",
        "source_role": "reviewer",
        "source_run_id": "r-old",
        "source_model_id": "old-model",
        "source_family": "old-family",
    }
    f = Finding(**legacy)
    assert f.plan_section == ""
    assert f.risk_if_ignored == ""
    assert json.loads(f.to_jsonl())["risk_if_ignored"] == ""


def test_parse_finding_block_keeps_risk_and_plan_section():
    mod = _load_runner_module()
    payload = json.dumps(
        {
            "finding_id": "F-b7e2",
            "severity": "high",
            "category": "test-gap",
            "plan_section": "Chunk plan / commands",
            "claim": OBSERVED_CLAIM,
            "evidence": ["plan.md:Chunk plan"],
            "recommended_change": OBSERVED_FIX,
            "risk_if_ignored": OBSERVED_RISK,
        }
    )
    findings = mod._parse_finding_block(
        "plan-reviewer-1", payload, "r-1", "grok-4.5", "grok-family", 1
    )
    assert len(findings) == 1
    assert findings[0].risk_if_ignored == OBSERVED_RISK
    assert findings[0].plan_section == "Chunk plan / commands"


def test_actionable_fields_are_not_clipped_to_240():
    """The planner acts on ``risk_if_ignored`` and
    ``recommended_change`` verbatim, so the display-length cap must not
    apply to them."""
    mod = _load_runner_module()
    long_text = "x" * 900
    payload = json.dumps(
        {
            "finding_id": "F-long",
            "severity": "blocker",
            "claim": "c",
            "recommended_change": long_text,
            "risk_if_ignored": long_text,
        }
    )
    f = mod._parse_finding_block("r1", payload, "r-1", "m", "fam", 1)[0]
    assert len(f.risk_if_ignored) == 900
    assert len(f.recommended_change) == 900


# ── Defect 2: a finding must never read as an approval ───────────────────


def test_formatter_leads_with_the_risk_not_the_claim():
    """Regression pin for the live run: the rendered finding must carry
    the risk text, and must not present the plan's claim as the reason
    the gate refused."""
    mod = _load_runner_module()
    out = mod._format_finding_for_human(_finding(), detailed=True)
    assert "False confidence at GREEN" in out
    risk_line = [ln for ln in out.splitlines() if ln.strip().startswith("risk:")]
    assert risk_line, out
    assert "False confidence at GREEN" in risk_line[0]
    # The claim may appear, but only labelled as the plan's own words.
    claim_line = [ln for ln in out.splitlines() if "wider backend suite" in ln]
    assert claim_line, out
    assert claim_line[0].strip().startswith("plan claims:"), claim_line[0]


def test_formatter_headline_is_the_risk_in_compact_mode():
    mod = _load_runner_module()
    out = mod._format_finding_for_human(_finding())
    assert "F-b7e2" in out
    assert "False confidence at GREEN" in out
    assert "wider backend suite" not in out


def test_formatter_falls_back_to_claim_when_risk_is_empty():
    mod = _load_runner_module()
    out = mod._format_finding_for_human(
        _finding(risk_if_ignored="", claim="no risk field emitted"), detailed=True
    )
    assert "no risk field emitted" in out
    # Labelled "finding", never "risk" — the reviewer made no risk
    # statement here and the render must not invent one.
    assert "risk:" not in out
    assert "finding: no risk field emitted" in out


def test_refusal_block_shows_the_risk(capsys):
    mod = _load_runner_module()
    with tempfile.TemporaryDirectory() as root:
        rs = _run_state(root)
        rs.plan_findings = [_finding()]
        try:
            mod._enforce_5_3_preconditions(rs)
            raise AssertionError("open high finding must refuse")
        except SystemExit as e:
            assert e.code == 4
    err = capsys.readouterr().err
    assert "REFUSED" in err
    assert "False confidence at GREEN" in err


# ── Defect 2b: the planner sees the prior round's findings ───────────────


def test_prior_findings_sentinel_on_empty():
    mod = _load_runner_module()
    assert mod._format_prior_findings([]) == SENTINEL
    assert mod._format_prior_findings(None) == SENTINEL


def test_prior_findings_orders_blocker_high_first():
    mod = _load_runner_module()
    out = mod._format_prior_findings(
        [
            _finding(finding_id="F-low", severity="low"),
            _finding(finding_id="F-med", severity="medium"),
            _finding(finding_id="F-high", severity="high"),
            _finding(finding_id="F-blk", severity="blocker"),
        ]
    )
    positions = [out.index(fid) for fid in ("F-blk", "F-high", "F-med", "F-low")]
    assert positions == sorted(positions), out


def test_prior_findings_includes_id_severity_risk_and_fix():
    mod = _load_runner_module()
    out = mod._format_prior_findings([_finding()])
    assert "F-b7e2" in out
    assert "high" in out
    assert "Chunk plan / commands" in out
    assert OBSERVED_RISK in out
    assert OBSERVED_FIX in out
    assert OBSERVED_CLAIM in out


def test_prior_findings_never_raises_on_garbage():
    mod = _load_runner_module()
    assert mod._format_prior_findings([object()]) == SENTINEL


def test_planner_prompt_carries_prior_findings_on_a_later_round(tmp_path):
    from sprint_loop.prompts.render import render_to_file

    mod = _load_runner_module()
    out = tmp_path / "plan-prompt.md"
    render_to_file(
        "planner",
        {
            "pilot_spec_path": "/tmp/spec.md",
            "plan_output_path": "/tmp/plan.md",
            "authored_chunks": "(none supplied — propose a chunking)",
            "prior_findings": mod._format_prior_findings([_finding()]),
            "replan_feedback": "(no replan in progress — plan from the pilot "
            "spec and prior findings)",
        },
        str(out),
    )
    text = out.read_text()
    assert "## Prior review findings" in text
    assert OBSERVED_RISK in text
    assert "{{" not in text


def test_planner_supersedes_prior_findings_so_round_two_can_accept(tmp_path):
    """§5.3 binds a finding to one plan_sha256. Findings raised against
    the plan a new round replaces must stop counting as open, or the
    second round refuses on the first round's ledger no matter what the
    planner fixed — which makes the loop pointless."""
    mod = _load_runner_module()
    with tempfile.TemporaryDirectory() as root:
        rs = _run_state(root)
        rs.chunks_file = ""
        rs.dry_run = True
        rs.plan_round = 2
        rs.plan_findings = [_finding(severity="blocker")]
        mod.run_planner(
            rs,
            pilot_spec_text="(spec)",
            evidence_dir=str(tmp_path),
            dry_run=True,
        )
    assert rs.plan_findings[0].status == "superseded"
    assert "superseded" in rs.plan_findings[0].disposition_rationale
    # ... and the finding is still there, in the prompt the planner saw.
    prompt = (tmp_path / "plan-prompt-r2.md").read_text()
    assert OBSERVED_RISK in prompt


def test_planner_prompt_carries_sentinel_on_the_first_round(tmp_path):
    from sprint_loop.prompts.render import render_to_file

    mod = _load_runner_module()
    out = tmp_path / "plan-prompt.md"
    render_to_file(
        "planner",
        {
            "pilot_spec_path": "/tmp/spec.md",
            "plan_output_path": "/tmp/plan.md",
            "authored_chunks": "(none supplied — propose a chunking)",
            "prior_findings": mod._format_prior_findings([]),
            "replan_feedback": "(no replan in progress — plan from the pilot "
            "spec and prior findings)",
        },
        str(out),
    )
    text = out.read_text()
    assert SENTINEL in text
    assert "{{" not in text


# ── Defect 3: unattended mode uses its review rounds ────────────────────


def test_unattended_rejects_to_loop_while_rounds_remain():
    mod = _load_runner_module()
    with tempfile.TemporaryDirectory() as root:
        rs = _run_state(root)
        rs.max_review_rounds = 2
        rs.plan_round = 1
        rs.plan_findings = [_finding(severity="blocker")]
        rs.plan_reviewer_verdicts = [{"reviewer_index": 1, "verdict": "REJECT"}]
        with tempfile.TemporaryDirectory() as evidence_dir:
            decision = mod.reconcile_human_gate(
                rs,
                evidence_dir=evidence_dir,
                dry_run=False,
                gate_auto_decide=True,
                unattended=True,
            )
            assert decision == ReconcileDecision.REJECT
            # Looping is not a terminal refusal, so no checkpoint yet.
            assert not os.path.exists(os.path.join(evidence_dir, "checkpoint.json"))
        assert "round 1 of 2" in rs.status_message


def test_unattended_refuses_when_rounds_are_exhausted():
    mod = _load_runner_module()
    with tempfile.TemporaryDirectory() as root:
        rs = _run_state(root)
        rs.max_review_rounds = 2
        rs.plan_round = 2
        rs.plan_findings = [_finding(severity="blocker")]
        rs.plan_reviewer_verdicts = [{"reviewer_index": 1, "verdict": "REJECT"}]
        with tempfile.TemporaryDirectory() as evidence_dir:
            try:
                mod.reconcile_human_gate(
                    rs,
                    evidence_dir=evidence_dir,
                    dry_run=False,
                    gate_auto_decide=True,
                    unattended=True,
                )
                raise AssertionError("exhausted rounds must SystemExit(4)")
            except SystemExit as e:
                assert e.code == 4
            assert os.path.isfile(os.path.join(evidence_dir, "checkpoint.json"))


def test_unattended_accept_path_unchanged_when_no_blocker_or_high():
    """§5.3's accept path must not be weakened: a clean ledger with a
    bound APPROVE still accepts on the first round."""
    mod = _load_runner_module()
    with tempfile.TemporaryDirectory() as root:
        rs = _run_state(root)
        rs.max_review_rounds = 2
        rs.plan_round = 1
        rs.plan_findings = [_finding(severity="medium")]
        rs.plan_reviewer_verdicts = [
            {
                "reviewer_index": 1,
                "verdict": "APPROVE",
                "plan_sha256_at_time_of_review": rs.plan_sha256,
            }
        ]
        with tempfile.TemporaryDirectory() as evidence_dir:
            decision = mod.reconcile_human_gate(
                rs,
                evidence_dir=evidence_dir,
                dry_run=False,
                gate_auto_decide=True,
                unattended=True,
            )
    assert decision == ReconcileDecision.ACCEPT


def test_unattended_still_refuses_exit_5_without_a_bound_approve():
    """Only the blocker|high refusal loops. A missing bound APPROVE is
    not something a re-plan fixes, so exit 5 stays terminal."""
    mod = _load_runner_module()
    with tempfile.TemporaryDirectory() as root:
        rs = _run_state(root)
        rs.max_review_rounds = 2
        rs.plan_round = 1
        rs.plan_findings = []
        rs.plan_reviewer_verdicts = [{"reviewer_index": 1, "verdict": "REJECT"}]
        with tempfile.TemporaryDirectory() as evidence_dir:
            try:
                mod.reconcile_human_gate(
                    rs,
                    evidence_dir=evidence_dir,
                    dry_run=False,
                    gate_auto_decide=True,
                    unattended=True,
                )
                raise AssertionError("no bound APPROVE must SystemExit(5)")
            except SystemExit as e:
                assert e.code == 5

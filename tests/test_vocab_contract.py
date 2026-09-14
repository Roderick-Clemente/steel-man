"""Protocol vocabulary stays aligned across prompts, parsers, and routing."""

from __future__ import annotations

import importlib.util
import os
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TOOLS = os.path.join(_REPO, "tools")
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)

from sprint_loop import per_chunk, vocab  # noqa: E402


def _load_orchestrator():
    path = os.path.join(_TOOLS, "orchestrate-review.py")
    spec = importlib.util.spec_from_file_location("orchestrate_review_vocab", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_validator_prompt_verdict_block_exactly_matches_vocab():
    prompt_path = os.path.join(
        _TOOLS, "sprint_loop", "prompts", "validator.md"
    )
    with open(prompt_path) as f:
        lines = [
            line
            for line in f.read().splitlines()
            if line.startswith("VERDICT:")
        ]
    assert lines == [f"VERDICT: {verdict}" for verdict in vocab.VALIDATOR_VERDICTS]


def test_orchestrator_parses_every_validator_verdict_from_its_last_tagged_line():
    orchestrator = _load_orchestrator()
    validators = [
        {
            "label": verdict,
            "ok": True,
            "result_text": (
                "Narration may mention ACCEPT, REJECT, or REPLAN.\n"
                f"VERDICT: {verdict}"
            ),
        }
        for verdict in vocab.VALIDATOR_VERDICTS
    ]
    parsed = orchestrator.step4_parse_verdicts(validators)
    assert [row["verdict"] for row in parsed] == list(vocab.VALIDATOR_VERDICTS)


def test_replan_is_advertised_and_parsed():
    """KI-19 fast follow: REPLAN was removed while unsupported and is now
    a first-class verdict again — advertised in the prompt and parsed by
    the orchestrator from the shared vocabulary."""
    assert "REPLAN" in vocab.VALIDATOR_VERDICTS
    orchestrator = _load_orchestrator()
    parsed = orchestrator.step4_parse_verdicts(
        [
            {
                "label": "replan-seat",
                "ok": True,
                "result_text": "VERDICT: REPLAN",
            }
        ]
    )
    assert parsed[0]["verdict"] == "REPLAN"


def test_orchestrator_gate_treats_replan_as_reject():
    """A REPLAN verdict must block the gate; letting it pass as an ACCEPT
    would reintroduce the KI-19 silent-green shape with the verdict now
    parseable."""
    orchestrator = _load_orchestrator()
    gate, reason = orchestrator.step6_gate_decision(
        [
            {"label": "v1", "ok": True, "is_error": False, "verdict": "REPLAN"},
            {"label": "v2", "ok": True, "is_error": False, "verdict": "ACCEPT"},
        ]
    )
    assert gate == "REJECT"
    assert "REPLAN" in reason


def test_orchestrator_gate_accepts_an_unrejected_panel():
    orchestrator = _load_orchestrator()
    gate, reason = orchestrator.step6_gate_decision(
        [
            {"label": "v1", "ok": True, "is_error": False, "verdict": "ACCEPT"},
            {"label": "v2", "ok": True, "is_error": False, "verdict": "ACCEPT-WITH-NITS"},
        ]
    )
    assert gate == "ACCEPT"
    assert "2 validator(s) ACCEPT" in reason


def test_test_directed_routing_uses_shared_verdict_vocab():
    assert per_chunk.TEST_DIRECTED_VERDICTS is vocab.TEST_DIRECTED_VERDICTS

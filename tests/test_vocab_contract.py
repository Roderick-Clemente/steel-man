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


def test_unsupported_replan_is_not_advertised_or_parsed():
    orchestrator = _load_orchestrator()
    parsed = orchestrator.step4_parse_verdicts(
        [
            {
                "label": "unsupported",
                "ok": True,
                "result_text": "VERDICT: REPLAN",
            }
        ]
    )
    assert "REPLAN" not in vocab.VALIDATOR_VERDICTS
    assert parsed[0]["verdict"] == "UNKNOWN"


def test_test_directed_routing_uses_shared_verdict_vocab():
    assert per_chunk.TEST_DIRECTED_VERDICTS is vocab.TEST_DIRECTED_VERDICTS

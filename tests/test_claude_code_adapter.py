"""Tests for tools/adapters/claude_code.py against a real captured run.

Fixture at tools/fixtures/claude-code-probe/{envelope,session}.jsonl
was captured live via:

    claude -p "Read the file test.txt if it exists, otherwise just
    reply with exactly: hello" --output-format json --model
    claude-haiku-4-5-20251001

on 2026-09-25. The prompt intentionally names a nonexistent file so
the fixture exercises a real tool_use -> failed tool_result pair,
not just a clean no-tool-call run.
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

from adapters import claude_code  # noqa: E402

FIXTURE_DIR = REPO_ROOT / "tools" / "fixtures" / "claude-code-probe"


def test_to_envelope_matches_contract_shape():
    envelope = claude_code.to_envelope(
        envelope_path=FIXTURE_DIR / "envelope.json",
        session_jsonl_path=FIXTURE_DIR / "session.jsonl",
    )
    assert set(envelope.keys()) == {
        "session_id",
        "is_error",
        "num_turns",
        "duration_ms",
        "tool_calls",
        "usage",
        "model_id",
        "family",
        "result_text",
        "result_text_first_240chars",
    }


def test_to_envelope_reads_top_level_fields():
    envelope = claude_code.to_envelope(
        envelope_path=FIXTURE_DIR / "envelope.json",
        session_jsonl_path=FIXTURE_DIR / "session.jsonl",
    )
    assert envelope["session_id"] == "4fe0ceb2-8871-4aa2-b36c-5b8ebbd15a69"
    assert envelope["is_error"] is False
    assert envelope["num_turns"] == 3
    assert envelope["duration_ms"] == 2168
    assert envelope["result_text"] == "hello"
    assert envelope["result_text_first_240chars"] == "hello"


def test_to_envelope_maps_usage_fields():
    envelope = claude_code.to_envelope(
        envelope_path=FIXTURE_DIR / "envelope.json",
        session_jsonl_path=FIXTURE_DIR / "session.jsonl",
    )
    assert envelope["usage"] == {
        "input": 10,
        "output": 116,
        "cache_read": 14630,
        "thinking": 0,
    }


def test_to_envelope_resolves_model_and_family_from_transcript():
    envelope = claude_code.to_envelope(
        envelope_path=FIXTURE_DIR / "envelope.json",
        session_jsonl_path=FIXTURE_DIR / "session.jsonl",
    )
    assert envelope["model_id"] == "claude-haiku-4-5-20251001"
    assert envelope["family"] == "anthropic"


def test_to_envelope_extracts_the_real_failed_tool_call():
    envelope = claude_code.to_envelope(
        envelope_path=FIXTURE_DIR / "envelope.json",
        session_jsonl_path=FIXTURE_DIR / "session.jsonl",
    )
    assert envelope["tool_calls"] == [
        {
            "name": "Read",
            "args": {
                "file_path": (
                    "/private/tmp/claude-501/-Users-dev-Work-life/"
                    "8bb4cc28-6cd0-4c17-8eac-55b03b3a1b4e/scratchpad/"
                    "claude-adapter-probe/test.txt"
                )
            },
            "is_error": True,
        }
    ]


def test_to_envelope_without_session_jsonl_returns_empty_tool_calls():
    envelope = claude_code.to_envelope(
        envelope_path=FIXTURE_DIR / "envelope.json",
        session_jsonl_path=Path("/nonexistent/path.jsonl"),
    )
    assert envelope["tool_calls"] == []
    # model_id still resolves via the modelUsage fallback, since the
    # fixture envelope has exactly one model key.
    assert envelope["model_id"] == "claude-haiku-4-5-20251001"


def test_locate_session_jsonl_returns_none_without_session_id():
    assert claude_code.locate_session_jsonl(None) is None


def test_fixture_files_are_the_real_captured_shape():
    """Sanity check the fixture itself hasn't drifted from a real run."""
    envelope = json.loads((FIXTURE_DIR / "envelope.json").read_text())
    assert envelope["type"] == "result"
    assert "modelUsage" in envelope
    lines = (FIXTURE_DIR / "session.jsonl").read_text().strip().splitlines()
    types = [json.loads(line)["type"] for line in lines]
    assert types == ["summary", "user", "assistant", "user", "assistant"]

"""Regression test for planner tool-policy claim (finding P2-c).

planner.md claims "You have no file-writing tool" (the planner emits a
plan as its final message; writing to disk is the runner's job). That
claim must be true: Execute in the planner allowlist lets the planner
write files and is the original KI-7 vector. Verify the allowlist
matches the prompt's claim.

The first two tests pin the ``DEFAULT_ENABLED_TOOLS`` dict; the third
pins the RunState the live entrypoint actually constructs, because the
N-1 defect was exactly that split — the dict was fixed while
``_main_inner`` kept handing seats its own hardcoded literals.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys

_TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)

from sprint_loop.state import DEFAULT_ENABLED_TOOLS, Role  # noqa: E402


def test_planner_has_no_execute_tool():
    """Execute must not be in the planner allowlist (KI-7 vector)."""
    tools = DEFAULT_ENABLED_TOOLS[Role.PLANNER].split(",")
    assert "Execute" not in tools, (
        f"Execute in planner allowlist reintroduces KI-7: "
        f"the planner can write to disk, but planner.md claims it cannot"
    )


def test_planner_tools_are_read_only():
    """All planner tools must be read-only file inspection tools."""
    allowed_read_only = {"Read", "Glob", "Grep", "LS"}
    tools = set(DEFAULT_ENABLED_TOOLS[Role.PLANNER].split(","))
    assert tools <= allowed_read_only, (
        f"Planner has non-read-only tools: {tools - allowed_read_only}"
    )


def test_every_dict_id_is_executable_editable_or_read_only():
    """The dict's NOTE promises every id is one the installed CLI
    accepts. Pin the valid set structurally: no id outside the
    known-good union may appear (the KI-2 hazard is an id the CLI
    rejects wholesale, which ships a 0-byte envelope)."""
    known_good = {"Read", "Glob", "Grep", "LS", "Edit", "Create", "Execute"}
    for role, tool_csv in DEFAULT_ENABLED_TOOLS.items():
        tools = set(tool_csv.split(","))
        assert tools <= known_good, (
            f"{role.value} allowlist has ids outside the verified CLI "
            f"registry: {tools - known_good}"
        )


def test_live_runstate_seat_tools_derive_from_the_dict(tmp_path):
    """The live path must build every seat from DEFAULT_ENABLED_TOOLS.

    The N-1 defect: PR 2 fixed the dict but ``_main_inner`` kept a
    hardcoded planner literal with ``Execute``, so the KI-7 fix never
    reached the live seats. Drive ``main()`` end to end in
    ``--dry-run`` (no droid calls; the same fixture shape the
    sprint-loop dry-run e2e uses) and assert on the RunState the
    entrypoint actually constructed. Against the old literals this
    fails: the planner seat would carry ``Execute`` instead of the
    dict value.
    """
    cfg_path = tmp_path / "cfg.json"
    cfg_payload = {
        "framework_root": str(tmp_path / "fw"),
        "pilot_root": str(tmp_path / "pilot"),
        "pilot_python": "/usr/bin/python3",
        "validators": [
            "grok-4.5:xai:grok-family:grok-4.5",
            "gemini-3.1-pro-preview:google:gemini-family:gemini-3.1-pro-preview",
        ],
        "plan_reviewer_2_model": "gemini-3.1-pro-preview",
    }
    cfg_path.write_text(json.dumps(cfg_payload))
    # Bootstrap a fake framework + pilot so the directory-validation passes.
    (tmp_path / "fw" / "tools" / "sprint_loop").mkdir(parents=True)
    (tmp_path / "fw" / "tools/phase-1-scripts").mkdir(parents=True)
    (tmp_path / "fw" / "tools/phase-3.2-evidence").mkdir(parents=True)
    (tmp_path / "fw" / "tools" / "orchestrate-review.py").write_text("# stub")
    (tmp_path / "pilot").mkdir()
    chunks_path = tmp_path / "chunks.json"
    chunks_path.write_text(
        json.dumps(
            {
                "chunks": [
                    {
                        "chunk_id": "c1",
                        "scope": "add /llms.txt route",
                        "observable_criteria": ["GET /llms.txt returns 200"],
                        "allowed_files": ["app.py"],
                        "locked_test_files": ["test/test_x.py"],
                        "commands": ["pytest test/test_x.py -v"],
                        "rollback": "git checkout HEAD -- app.py",
                        "accepted_assertion": "GET /llms.txt returns 200",
                    }
                ],
            }
        )
    )
    runner_path = os.path.abspath(os.path.join(_TOOLS, "sprint-loop.py"))
    # Load the runner as a module (same shape the conftest helpers use);
    # runpy returns a derived namespace dict that main()'s globals do not
    # write back into, which would read a stale _CURRENT_RUN_STATE.
    spec = importlib.util.spec_from_file_location("sprint_loop_runner_no_execute", runner_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["sprint_loop_runner_no_execute"] = mod
    spec.loader.exec_module(mod)
    saved = list(sys.argv)
    try:
        sys.argv = [
            "sprint-loop.py",
            "--config",
            str(cfg_path),
            "--chunks-file",
            str(chunks_path),
            "--dry-run",
            "--non-interactive",
        ]
        rc = mod.main()
    finally:
        sys.argv = saved
    assert rc == 0, f"runner exited {rc}"

    rs = mod._CURRENT_RUN_STATE
    assert rs is not None, "main() must leave the constructed RunState on _CURRENT_RUN_STATE"

    # The KI-7 pin on the LIVE constructed seat, not just the dict:
    # the planner the run would actually invoke must not have Execute.
    assert rs.planner.enabled_tools == DEFAULT_ENABLED_TOOLS[Role.PLANNER]
    assert "Execute" not in rs.planner.enabled_tools.split(",")

    # Every seat derives from the single source — the N-1 consolidation.
    assert rs.plan_reviewer.enabled_tools == DEFAULT_ENABLED_TOOLS[Role.PLAN_REVIEWER]
    assert (
        rs.plan_reviewer_2 is not None
        and rs.plan_reviewer_2.enabled_tools
        == DEFAULT_ENABLED_TOOLS[Role.PLAN_REVIEWER]
    )
    assert rs.test_designer.enabled_tools == DEFAULT_ENABLED_TOOLS[Role.TEST_DESIGNER]
    assert rs.executor.enabled_tools == DEFAULT_ENABLED_TOOLS[Role.EXECUTOR]
    assert all(
        v.enabled_tools == DEFAULT_ENABLED_TOOLS[Role.VALIDATOR] for v in rs.validators
    )

    # The sibling drift KI-2 documents: no seat may be handed an id the
    # installed CLI rejects. ApplyPatch/MultiEdit are the historical
    # offenders; neither may come back through the single source.
    for seat in (rs.test_designer, rs.executor):
        tools = seat.enabled_tools.split(",")
        assert "ApplyPatch" not in tools and "MultiEdit" not in tools, seat.enabled_tools

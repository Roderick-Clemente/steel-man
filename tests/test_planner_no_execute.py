"""Regression test for planner tool-policy claim (finding P2-c).

planner.md claims "You have no file-writing tool" (the planner emits a
plan as its final message; writing to disk is the runner's job). That
claim must be true: Execute in the planner allowlist lets the planner
write files and is the original KI-7 vector. Verify the allowlist
matches the prompt's claim.
"""

from __future__ import annotations

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

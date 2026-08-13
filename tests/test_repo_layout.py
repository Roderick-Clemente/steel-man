"""Top-level clutter gate: adding a root entry requires touching this list.

Stray files accreted at repo root (three phase-4 review artifacts sat there
for a week) because nothing made root membership a decision. This test does.
"""

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

ALLOWED_TOP_LEVEL = frozenset({
    ".claude",
    ".cursor",
    ".factory",
    ".github",
    ".gitignore",
    "AGENTS.md",
    "LICENSE",
    "NOTICE",
    "PRD.md",
    "README.md",
    "build-evidence",
    "droid-wiki",
    "phase-0",
    "phase-1",
    "phase-2",
    "phase-3",
    "phase-3.1",
    "phase-3.2",
    "phase-3.3",
    "phase-4",
    "phase-4.5",
    "phase-5",
    "pilots",
    "planning",
    "pytest.ini",
    "skills",
    "telemetry",
    "templates",
    "tests",
    "tools",
})


def tracked_top_level_entries():
    out = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return {line.split("/", 1)[0] for line in out.splitlines() if line}


def test_top_level_entries_are_allowlisted():
    entries = tracked_top_level_entries()
    strays = entries - ALLOWED_TOP_LEVEL
    assert not strays, (
        f"top-level entries not in the allowlist: {sorted(strays)} — "
        "either move them into an existing directory or add them here "
        "deliberately"
    )

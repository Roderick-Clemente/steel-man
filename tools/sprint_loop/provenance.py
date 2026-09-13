"""Run provenance for telemetry rows (SCHEMA.md v3).

Lives in the ``sprint_loop`` package rather than in ``sprint-loop.py``
because ``per_chunk.py`` also stamps rows and cannot import a
hyphenated script module.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sprint_loop.state import RunState


def _git_sha(repo_root: str) -> str:
    """HEAD sha of a repo, or "unknown" if it can't be read."""
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_root,
                             capture_output=True, text=True, timeout=10)
        return out.stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def _git_branch(repo_root: str) -> str:
    """Current branch of a repo, or "unknown"/"detached"."""
    try:
        out = subprocess.run(["git", "branch", "--show-current"], cwd=repo_root,
                             capture_output=True, text=True, timeout=10)
        return out.stdout.strip() or "detached"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def run_provenance(rs: "RunState") -> dict:
    """Provenance stamped on every telemetry row of this run (v3).

    Without the runner sha and the active flags on the row itself, an
    "efficacy over time" series silently mixes runner versions and run
    modes, and no later query can separate them.
    """
    return {
        "run_label": rs.run_label,
        "framework_sha": _git_sha(rs.framework_root),
        "framework_branch": _git_branch(rs.framework_root),
        "pilot_root": rs.pilot_root,
        "pilot_head": _git_sha(rs.pilot_root),
        "plan_sha256": rs.plan_sha256,
        "plan_round": rs.plan_round,
        "flag_unattended": bool(rs.unattended),
        "flag_force_accept": bool(rs.force_accept),
        "flag_verify_mode": bool(rs.verify_mode),
        "flag_dry_run": bool(rs.dry_run),
        "flag_skip_reconcile": bool(rs.skip_reconcile),
    }

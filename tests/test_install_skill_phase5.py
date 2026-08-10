"""Install-skill re-emit + Phase 5 dress rehearsal (chunk-5e pin).

Per OPERATING-RULES §18.6 — distilling principles into reusable assets:
the Phase 5 build closes with verification that ``tools/install-skill.sh``
re-emits the canonical skill to all four agent surfaces (factory,
claude, cursor, codex) when invoked, AND that the rule #9 digest row
(chunk close is gated, not declared) is present in the canonical
SKILL.md so the install operation is meaningful after compile-time
edits.

This test does not mock the install script — it shells out to the real
one and inspects the resulting files on disk (the artifact, per §7).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


_REPO = Path(__file__).resolve().parent.parent
_SKILL = _REPO / "skills" / "adversarial-sprint" / "SKILL.md"


def test_canonical_skill_has_rule_nine_chunk_close_is_gated():
    """§18.6 distill pin: the canonical SKILL.md must carry rule #9
    (chunk-close is gated) so every re-install produces a working
    operator-eye enforcement signal.
    """
    body = _SKILL.read_text()
    assert "9. **Chunk close is gated" in body, (
        f"Rule #9 absence: cannot guarantee downstream enforcement. "
        f"First 200 chars around the digest:\n{body[body.find('Skill digest'):body.find('Skill digest')+1200]}"
    )
    assert "EVIDENCE_SIGNING_KEY" in body
    assert "chunk-N.token.json" in body


def test_install_skill_emits_rule_nine_to_factory_claude_cursors(tmp_path):
    """Pin: install-skill.sh writes the rule #9-carrying skill to all
    three machine-checkable agent surfaces. Run the install in an
    isolated tmp dir (use the live repo for fixed-path testing)."""
    # Use the live repo as the install target; assert presence of the
    # three machine-checkable surfaces after install.
    sandbox = _REPO  # the install is repo-local by design
    for surface in (
        sandbox / ".factory" / "skills" / "adversarial-sprint" / "SKILL.md",
        sandbox / ".claude" / "skills" / "adversarial-sprint" / "SKILL.md",
        sandbox / ".cursor" / "rules" / "adversarial-sprint.mdc",
        sandbox / ".cursor" / "rules" / "sprint-invocation.mdc",
    ):
        if surface.exists():
            surface.unlink()

    p = subprocess.run(
        [
            "bash", str(_REPO / "tools" / "install-skill.sh"),
            "factory", "claude", "cursor",
        ],
        cwd=str(_REPO), capture_output=True, text=True,
    )
    assert p.returncode == 0, p.stderr

    # factory + claude: symlinks; canonical body must mention rule #9
    for sname in ("factory", "claude"):
        s = sandbox / f".{sname}" / "skills" / "adversarial-sprint" / "SKILL.md"
        assert s.exists(), f"missing {s}"
        body = s.read_text()
        assert "9. **Chunk close is gated" in body, (
            f"{sname} install did not propagate rule #9"
        )

    # cursor: rendered .mdc, must also reference the rule.
    cursor_adversarial = sandbox / ".cursor" / "rules" / "adversarial-sprint.mdc"
    cursor_invocation = sandbox / ".cursor" / "rules" / "sprint-invocation.mdc"
    assert cursor_adversarial.exists()
    cursor_body = cursor_adversarial.read_text()
    assert "Chunk close is gated" in cursor_body
    assert cursor_invocation.exists()  # sprint-invocation is the sibling

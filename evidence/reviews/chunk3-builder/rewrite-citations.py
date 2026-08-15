#!/usr/bin/env python3
"""chunk-D1-3 citation rewrite — the exact transformation applied to the §2.1a
surface, scripted so a reviewer can re-run it and diff rather than take the
diff on faith (§9).

Idempotent: every replacement is anchored with the same negative lookbehind the
judge uses for residual detection, so a token that has already been re-rooted
(``evidence/phase-3/``) is invisible to it. Re-running on a rewritten tree makes
zero changes and reports 0 for every rule.

Scope discipline (CHUNK-3-SPEC §2.1a / §2.1b): only the files listed in
``TARGETS`` are opened for writing. ``droid-wiki/by-the-numbers.md`` and
``droid-wiki/lore.md`` are deliberately ABSENT — they are a measurement snapshot
and a build history respectively, and rewriting their tokens would falsify a
record rather than fix a link (see FINDINGS §F1/§F2). Their residuals are
enumerated in ``planning/PATH-REDIRECTS.md`` instead, which is what §2.3 asks
for. Nothing under ``planning/layout-refactor/`` or ``planning/phase-N/`` is
touched at all.

Usage: python3 rewrite-citations.py [--check]
  --check   report what would change, write nothing (rc=1 if anything would)
"""
from __future__ import annotations

import os
import re
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

# Old citation -> new home. Longest key first at match time, so
# `phase-3.2/evidence/consumer.py` wins over `phase-3.2/evidence/`.
#
# Two roots, not one: chunk-D1-2 split each phase silo by KIND, so the correct
# destination depends on what the cited thing IS. Planning prose went to
# `planning/phase-N/`, committed evidence to `evidence/phase-N/`, and executable
# code to `tools/phase-N-<subdir>/`. `phase-3.2/evidence/` is the sharpest case:
# `consumer.py` is code (tools/), `bundle_schema_v1.json` is data (evidence/).
MAP = {
    # phase-0
    "phase-0/GO-NO-GO.md": "planning/phase-0/GO-NO-GO.md",
    "phase-0/README.md": "planning/phase-0/README.md",
    "phase-0/evidence/canary-0.180.0/": "evidence/phase-0/canary-0.180.0/",
    "phase-0/evidence/": "evidence/phase-0/",
    # phase-1
    "phase-1/KNOWN-ISSUES.md": "planning/phase-1/KNOWN-ISSUES.md",
    "phase-1/scripts/": "tools/phase-1-scripts/",
    "phase-1/locks/": "tools/phase-1-locks/",
    # phase-2 / phase-3
    "phase-2/build-evidence/": "evidence/phase-2/build-evidence/",
    "phase-3/build-evidence/": "evidence/phase-3/build-evidence/",
    # phase-3.1
    "phase-3.1/build-evidence/": "evidence/phase-3.1/build-evidence/",
    "phase-3.1/RESULTS.md": "planning/phase-3.1/RESULTS.md",
    # phase-3.2 — code to tools/, data and envelopes to evidence/, prose to planning/
    "phase-3.2/evidence/bundle_schema_v1.json": "evidence/phase-3.2/bundle_schema_v1.json",
    "phase-3.2/evidence/consumer.py": "tools/phase-3.2-evidence/consumer.py",
    "phase-3.2/evidence/": "tools/phase-3.2-evidence/",
    "phase-3.2/reviews/": "evidence/phase-3.2/reviews/",
    "phase-3.2/BUILD-NOTES.md": "planning/phase-3.2/BUILD-NOTES.md",
    "phase-3.2/SPIKE.md": "planning/phase-3.2/SPIKE.md",
    # phase-3.3
    "phase-3.3/SPIKE.md": "planning/phase-3.3/SPIKE.md",
    # phase-4.5
    "phase-4.5/tokens/": "evidence/phase-4.5/tokens/",
    "phase-4.5/build-evidence/": "evidence/phase-4.5/build-evidence/",
    "phase-4.5/DESIGN-DAEMON-SIGNER.md": "planning/phase-4.5/DESIGN-DAEMON-SIGNER.md",
    "phase-4.5/DESIGN-PERSISTENT-REFEREE.md": "planning/phase-4.5/DESIGN-PERSISTENT-REFEREE.md",
    "phase-4.5/DESIGN-REVIEW-ATTESTATION-GATE.md": "planning/phase-4.5/DESIGN-REVIEW-ATTESTATION-GATE.md",
    "phase-4.5/KNOWN-ISSUES.md": "planning/phase-4.5/KNOWN-ISSUES.md",
    "phase-4.5/RUN-PROMPT.md": "planning/phase-4.5/RUN-PROMPT.md",
    "phase-4.5/prompts/": "planning/phase-4.5/prompts/",
    # phase-5
    "phase-5/DESIGN-ROLE-SPLIT-AND-SIGNALS.md": "planning/phase-5/DESIGN-ROLE-SPLIT-AND-SIGNALS.md",
}

# A bare directory token — `phase-0/` with nothing after it — has no unique new
# home, because chunk-2 split each silo across two or three roots. It is only
# rewritten where the surrounding prose says which kind is meant. In
# ROADMAP-REVIEW-PROMPT.md the list is introduced by "Every phase directory's
# README / RESULTS / BUILD-NOTES / ASSUMPTIONS", all of which are planning docs.
PER_FILE = {
    "planning/ROADMAP-REVIEW-PROMPT.md": {
        f"phase-{n}/": f"planning/phase-{n}/"
        for n in ("0", "1", "2", "3", "3.1", "3.2", "3.3")
    },
}

# Markdown link TARGETS need their own pass, and the reason is worth stating: a
# target is written `](./phase-3.1/RESULTS.md)`, so the character before the
# token is `/`, which LOOKBEHIND deliberately excludes — the same exclusion that
# stops `evidence/phase-3/` being rewritten twice. The judge's residual matcher
# has the identical blind spot, which is why §3.1 asserts on link RESOLUTION
# instead of on token counts: rewriting only the visible label would leave the
# href still 404ing on GitHub and every token check would still read clean.
LINK_FIXES = {
    "README.md": {
        "](./phase-3.1/RESULTS.md)": "](./planning/phase-3.1/RESULTS.md)",
        "](./phase-5/DESIGN-ROLE-SPLIT-AND-SIGNALS.md)":
            "](./planning/phase-5/DESIGN-ROLE-SPLIT-AND-SIGNALS.md)",
        "](./phase-1/KNOWN-ISSUES.md)": "](./planning/phase-1/KNOWN-ISSUES.md)",
    },
}

# Stale tails, corrected because a re-rooted path that still 404s is the
# silent-green shape §7 forbids: it LOOKS swept. Both referents were verified on
# disk, and `git log` shows the file was named `-spawn.md` when it was added
# (6c315a2) — the rule text never matched it, so this predates the move.
TAIL_FIXES = {
    "tools/OPERATING-RULES.md": {
        "planning/phase-4.5/prompts/phase-5-grok-validator.md":
            "planning/phase-4.5/prompts/phase-5-grok-validator-spawn.md",
        "planning/phase-4.5/prompts/phase-5-gemini-validator.md":
            "planning/phase-4.5/prompts/phase-5-gemini-validator-spawn.md",
    },
}

TARGETS = (
    "AGENTS.md",
    "PRD.md",
    "README.md",
    "droid-wiki/security.md",
    "planning/ROADMAP-REVIEW.md",
    "planning/ROADMAP-REVIEW-PROMPT.md",
    "skills/adversarial-sprint/SKILL.md",
    "skills/sprint-invocation/SKILL.md",
    "tools/OPERATING-RULES.md",
    "tools/conventions/model-discipline.md",
    "tools/sprint_loop/prompts/executor.md",
    "tools/sprint_loop/prompts/test-designer.md",
    "tools/sprint_loop/prompts/validator.md",
)

# Same lookbehind as the judge's residual matcher: an already-rooted token
# (`evidence/phase-3/`, `tools/phase-1-scripts/`) must never be rewritten twice.
LOOKBEHIND = r"(?<![/A-Za-z0-9_.\-])"


def rules_for(rel: str) -> list[tuple[str, str]]:
    merged = dict(MAP)
    merged.update(PER_FILE.get(rel, {}))
    # Longest old-token first: prefix keys must not shadow their own children.
    return sorted(merged.items(), key=lambda kv: -len(kv[0]))


def main() -> int:
    check = "--check" in sys.argv[1:]
    grand = 0
    for rel in TARGETS:
        path = os.path.join(REPO_ROOT, rel)
        with open(path, encoding="utf-8") as fh:
            text = original = fh.read()
        per_file = []
        for old, new in rules_for(rel):
            text, n = re.subn(LOOKBEHIND + re.escape(old), new, text)
            if n:
                per_file.append((old, new, n))
        for old, new in LINK_FIXES.get(rel, {}).items():
            text, n = re.subn(re.escape(old), new, text)
            if n:
                per_file.append((old, new, n))
        for old, new in TAIL_FIXES.get(rel, {}).items():
            text, n = re.subn(re.escape(old), new, text)
            if n:
                per_file.append((old, new, n))
        total = sum(n for _, _, n in per_file)
        grand += total
        if total:
            print(f"{rel}: {total} rewrite(s)")
            for old, new, n in per_file:
                print(f"    {n:3d}x  {old}  ->  {new}")
        if text != original and not check:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
    print(f"\ntotal: {grand} rewrite(s) across {len(TARGETS)} file(s)"
          f"{' (check only, nothing written)' if check else ''}")
    return 1 if (check and grand) else 0


if __name__ == "__main__":
    sys.exit(main())

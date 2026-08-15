#!/usr/bin/env python3
"""§4.4 — resolve every relative markdown link on the §2.1a surface and report
**count checked alongside count dead**.

The spec is explicit that this must not be hand-checked: a link that 404s on
GitHub is exactly the class a human eye skips. It is also explicit that
`tools/wiki-link-audit.py` must not be substituted — that tool walks only
`droid-wiki/` and reports `dead=0` on the very commit where `README.md` carries
four dead links.

Reporting the CHECKED count matters as much as the dead count: "0 dead" is
worthless if the resolver silently examined nothing (§7 — a check that can pass
because it ran on nothing is worse than no check). This script therefore exits
non-zero if the checked count is zero, and prints per-file counts so the total
can be audited rather than trusted.

Resolution mirrors `tests/test_layout_paths_chunk3.py::_..._every_relative_link_resolves`:
anchors and URL schemes are skipped, `#fragment`/`?query` are stripped, and a
target resolves if it exists relative to the citing file's directory OR relative
to the repo root (README-style `./planning/...` links satisfy the first form).

Usage: python3 dead-links.py
"""
from __future__ import annotations

import glob
import os
import re
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

MD_LINK = re.compile(r"\]\(([^)]+)\)")
SCHEME = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*:")

SURFACE_FILES = (
    "PRD.md",
    "AGENTS.md",
    "README.md",
    "tools/OPERATING-RULES.md",
    "tools/README.md",
    "tools/KNOWN-ISSUES.md",
    "tools/PHASE-0.5-CLOSE.md",
    "tools/RUN-LEDGER.md",
    "tools/REPRODUCE.md",
    "skills/adversarial-sprint/SKILL.md",
    "skills/sprint-invocation/SKILL.md",
)
SURFACE_GLOBS = (
    "tools/conventions/*.md",
    "tools/sprint_loop/prompts/*.md",
    "droid-wiki/*.md",
    "planning/ROADMAP-REVIEW*.md",
)


def surface() -> list[str]:
    out = [rel for rel in SURFACE_FILES if os.path.isfile(os.path.join(REPO_ROOT, rel))]
    for pattern in SURFACE_GLOBS:
        for abs_path in sorted(glob.glob(os.path.join(REPO_ROOT, pattern))):
            out.append(os.path.relpath(abs_path, REPO_ROOT))
    return sorted(set(out))


def main() -> int:
    checked = 0
    dead: list[str] = []
    per_file: list[tuple[str, int, int]] = []

    for rel in surface():
        abs_path = os.path.join(REPO_ROOT, rel)
        base = os.path.dirname(abs_path)
        n_checked = n_dead = 0
        with open(abs_path, encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, start=1):
                for match in MD_LINK.finditer(line):
                    target = match.group(1).strip()
                    if not target or target.startswith("#"):
                        continue
                    if SCHEME.match(target):
                        continue  # http:, mailto:, …
                    path = target.split("#", 1)[0].split("?", 1)[0].strip()
                    if not path:
                        continue
                    n_checked += 1
                    if os.path.exists(os.path.join(base, path)) or os.path.exists(
                        os.path.join(REPO_ROOT, path)
                    ):
                        continue
                    n_dead += 1
                    dead.append(f"{rel}:{lineno} -> {target}")
        checked += n_checked
        per_file.append((rel, n_checked, n_dead))

    print(f"§4.4 relative-link resolution over {len(surface())} surface files")
    print(f"{'file':<48} {'checked':>8} {'dead':>6}")
    for rel, n_checked, n_dead in per_file:
        print(f"{rel:<48} {n_checked:>8} {n_dead:>6}")
    print(f"{'TOTAL':<48} {checked:>8} {len(dead):>6}")

    if dead:
        print("\ndead:")
        for row in dead:
            print(f"  {row}")

    if checked == 0:
        print("\nREFUSING to report a green: 0 links checked means the resolver "
              "ran on nothing (§7).", file=sys.stderr)
        return 2
    return 1 if dead else 0


if __name__ == "__main__":
    sys.exit(main())

"""Template renderer for the role prompts.

Variables are ``{{key}}`` placeholders. The renderer reads a template
file from ``tools/sprint_loop/prompts/<role>.md``, substitutes the
variables from a context dict, and writes the rendered file to an
output path.

The renderer does NOT call ``tools/render-blind-prompt.py`` directly —
that tool exists to strip executor context from reviewer prompts and
runs as a separate pass for the plan-reviewer role only (the runner
calls it via ``subprocess.run`` — see ``tools/sprint_loop/orchestrator.py``).
This module is a simple, safe variable-substitution helper that any
role invocation can use.

Two safeguards:
  - Unknown ``{{key}}`` are *left untouched* in the output, so a
    careful reviewer can spot a missing context entry rather than
    silently substituting an empty string.
  - Rendering does not chmod or modify the template file. The output
    is written to a sibling path the caller controls.

Tests live in ``tests/test_sprint_loop.py``.
"""
from __future__ import annotations

import os
import re
import sys
from typing import Any

# Match {{key}} allow alphanum + underscore + dash. Conservative —
# anything outside this set is left intact (per the safeguard above).
_VAR_RE = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_-]*)\s*\}\}")

# Make sibling imports resolve when invoked as a script
_PROMPT_DIR = os.path.dirname(os.path.abspath(__file__))


def list_role_prompts() -> list[str]:
    """Return the role names (= .md filenames without extension)."""
    return sorted(
        os.path.splitext(f)[0]
        for f in os.listdir(_PROMPT_DIR)
        if f.endswith(".md")
    )


def render(template_path: str, context: dict[str, Any]) -> str:
    """Render the template against the context.

    Returns the rendered text. Unknown variables remain as ``{{key}}``
    in the output so a missing context key is loud, not silent.
    """
    if not os.path.isfile(template_path):
        raise FileNotFoundError(
            f"prompt template not found: {template_path} (the role "
            f"prompt will not be substituted)"
        )
    with open(template_path) as f:
        text = f.read()

    def substitute(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in context:
            # Leave the placeholder in place — loud failure beats silent.
            return match.group(0)
        value = context[key]
        if value is None:
            return match.group(0)
        return str(value)

    return _VAR_RE.sub(substitute, text)


def render_to_file(role: str, context: dict[str, Any], output_path: str) -> str:
    """Render ``prompts/<role>.md`` against ``context`` to ``output_path``.

    Returns the absolute path of the rendered file.
    """
    template_path = os.path.join(_PROMPT_DIR, f"{role}.md")
    rendered = render(template_path, context)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        f.write(rendered)
    return os.path.abspath(output_path)


# ── CLI entry: inspect templates ─────────────────────────────────────────

def _cli(argv: list[str]) -> int:
    """Tiny shell driver.

    Usage:
      python3 -m sprint_loop.prompts.render list
      python3 -m sprint_loop.prompts.render render <role> <output_path> KEY=VAL KEY2=VAL2 ...
    """
    if not argv:
        print(__doc__, file=sys.stderr)
        return 2
    cmd = argv[0]
    if cmd == "list":
        for r in list_role_prompts():
            print(r)
        return 0
    if cmd == "render":
        if len(argv) < 3:
            print("usage: render <role> <output_path> KEY=VAL ...", file=sys.stderr)
            return 2
        role, output_path = argv[1], argv[2]
        context: dict[str, Any] = {}
        for kv in argv[3:]:
            if "=" not in kv:
                print(f"skipping malformed KV: {kv!r}", file=sys.stderr)
                continue
            k, v = kv.split("=", 1)
            context[k.strip()] = v.strip()
        render_to_file(role, context, output_path)
        print(output_path)
        return 0
    print(f"unknown subcommand: {cmd!r}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))

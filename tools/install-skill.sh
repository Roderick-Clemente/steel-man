#!/usr/bin/env bash
# install-skill.sh — install the project's adversarial-sprint skill
# to a target agent's known install path. The canonical source is
# skills/<name>/SKILL.md in this repo. Per-agent yml-frontmatter
# compatibility is documented in tools/conventions/skill-distribution.md.
#
# Usage:  ./tools/install-skill.sh [--dry-run] <agent>...
#         agents: factory | claude | cursor | codex | all
#         skills (when installing all): sprint-invocation is included
#
# This is the bootstrap install for external adopters. In-project
# commits already wire the symlinks / generated mdc files directly
# (see .factory/skills/, .claude/skills/, .cursor/rules/).

set -euo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "$PWD")"
DRY_RUN=0

if [ "${1:-}" = "--dry-run" ]; then DRY_RUN=1; shift; fi

SKILLS=("adversarial-sprint" "sprint-invocation")

# Per-agent install for a single skill (adapter-side abstraction).
install_one() {
  local skill="$1"
  local agent="$2"
  case "$agent" in
    factory)
      mkdir -p "$REPO_ROOT/.factory/skills/$skill"
      DEST="$REPO_ROOT/.factory/skills/$skill/SKILL.md"
      SOURCE="$REPO_ROOT/skills/$skill/SKILL.md"
      if [ "$DRY_RUN" = 1 ]; then echo "ln -sfn ../../../skills/$skill/SKILL.md $DEST"; return 0; fi
      ln -sfn ../../../skills/$skill/SKILL.md "$DEST"
      echo "[factory/$skill] $DEST -> $SOURCE"
      ;;
    claude)
      mkdir -p "$REPO_ROOT/.claude/skills/$skill"
      DEST="$REPO_ROOT/.claude/skills/$skill/SKILL.md"
      SOURCE="$REPO_ROOT/skills/$skill/SKILL.md"
      if [ "$DRY_RUN" = 1 ]; then echo "ln -sfn ../../../skills/$skill/SKILL.md $DEST"; return 0; fi
      ln -sfn ../../../skills/$skill/SKILL.md "$DEST"
      echo "[claude/$skill] $DEST -> $SOURCE"
      ;;
    cursor)
      mkdir -p "$REPO_ROOT/.cursor/rules"
      DEST="$REPO_ROOT/.cursor/rules/$skill.mdc"
      SOURCE="$REPO_ROOT/skills/$skill/SKILL.md"
      ALWAYS_APPLY="true"
      if [ "$skill" = "sprint-invocation" ]; then ALWAYS_APPLY="false"; fi
      if [ "$DRY_RUN" = 1 ]; then echo "generate $DEST from $SOURCE"; return 0; fi
      python3 - "$SOURCE" "$DEST" "$ALWAYS_APPLY" <<'PYEOF'
import sys, pathlib
src, dst, always_apply = sys.argv[1], sys.argv[2], sys.argv[3]
canonical = pathlib.Path(src).read_text()
parts = canonical.split('---', 2)
body = parts[-1].lstrip('\n')
globs_line = "globs: []\n" if always_apply == "false" else ""
fm = (
  '---\n'
  f'description: {canonical.split("description:",1)[1].split("---",1)[0].strip()}\n'
  f'alwaysApply: {always_apply}\n'
  f'{globs_line}'
  '---\n\n'
)
pathlib.Path(dst).write_text(fm + body)
PYEOF
      echo "[cursor/$skill] wrote $DEST from $SOURCE"
      ;;
    codex)
      DEST="$REPO_ROOT/AGENTS.md"
      if [ "$DRY_RUN" = 1 ]; then echo "append picker for $skill to $DEST"; return 0; fi
      if ! grep -q "skills/$skill/SKILL.md" "$DEST"; then
        printf '\n## Skill asset: %s\n\nSee `skills/%s/SKILL.md` for the project'\''s %s skill.\n' "$skill" "$skill" "$skill" >> "$DEST"
        echo "[codex/$skill] appended pointer to $DEST"
      else
        echo "[codex/$skill] pointer already in $DEST"
      fi
      ;;
    *)
      echo "unknown agent: $agent" >&2
      return 1
      ;;
  esac
}

if [ "${1:-}" = "all" ]; then
  shift
  AGENTS="factory claude cursor codex"
  if [ "$#" -gt 0 ]; then AGENTS="$@"; fi
  for skill in "${SKILLS[@]}"; do
    for agent in $AGENTS; do
      install_one "$skill" "$agent" || echo "failed: $skill on $agent"
    done
  done
  exit 0
fi

# Per-agent, all skills
if [ "$#" -eq 0 ]; then
  echo "usage: $0 [--dry-run] <factory|claude|cursor|codex|all>" >&2
  exit 1
fi
for agent in "$@"; do
  for skill in "${SKILLS[@]}"; do
    install_one "$skill" "$agent" || echo "failed: $skill on $agent"
  done
done

#!/usr/bin/env bash
# install-skill.sh — install the project's adversarial-sprint skill
# to a target agent's known install path. The canonical source is
# skills/<name>/SKILL.md in this repo. Per-agent yml-frontmatter
# compatibility is documented in tools/conventions/skill-distribution.md.
#
# Usage:  ./tools/install-skill.sh [--dry-run] <agent>...
#         agents: factory | claude | cursor | codex | all
#
# This is the bootstrap install for external adopters. In-project
# commits already wire the symlinks / generated mdc files directly
# (see .factory/skills/, .claude/skills/, .cursor/rules/).

set -euo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "$PWD")"
DRY_RUN=0

if [ "${1:-}" = "--dry-run" ]; then DRY_RUN=1; shift; fi

case "${1:-}" in
  factory)
    mkdir -p "$REPO_ROOT/.factory/skills/adversarial-sprint"
    DEST="$REPO_ROOT/.factory/skills/adversarial-sprint/SKILL.md"
    SOURCE="$REPO_ROOT/skills/adversarial-sprint/SKILL.md"
    if [ "$DRY_RUN" = 1 ]; then echo "ln -sfn $SOURCE $DEST"; exit 0; fi
    ln -sfn "$SOURCE" "$DEST"
    echo "[factory] $DEST -> $SOURCE"
    ;;
  claude)
    mkdir -p "$REPO_ROOT/.claude/skills/adversarial-sprint"
    DEST="$REPO_ROOT/.claude/skills/adversarial-sprint/SKILL.md"
    SOURCE="$REPO_ROOT/skills/adversarial-sprint/SKILL.md"
    if [ "$DRY_RUN" = 1 ]; then echo "ln -sfn $SOURCE $DEST"; exit 0; fi
    ln -sfn "$SOURCE" "$DEST"
    echo "[claude] $DEST -> $SOURCE"
    ;;
  cursor)
    mkdir -p "$REPO_ROOT/.cursor/rules"
    DEST="$REPO_ROOT/.cursor/rules/adversarial-sprint.mdc"
    SOURCE="$REPO_ROOT/skills/adversarial-sprint/SKILL.md"
    if [ "$DRY_RUN" = 1 ]; then echo "generate $DEST from $SOURCE"; exit 0; fi
    python3 - "$SOURCE" "$DEST" <<'PYEOF'
import sys, pathlib
src, dst = sys.argv[1], sys.argv[2]
canonical = pathlib.Path(src).read_text()
parts = canonical.split('---', 2)
body = parts[-1].lstrip('\n')
fm = (
  '---\n'
  'description: Adversarial sprint skill — read skills/adversarial-sprint/SKILL.md for the canonical body.\n'
  'alwaysApply: true\n'
  '---\n\n'
)
pathlib.Path(dst).write_text(fm + body)
PYEOF
    echo "[cursor] wrote $DEST from $SOURCE"
    ;;
  codex)
    DEST="$REPO_ROOT/AGENTS.md"
    MARK='When operating as the **planner / executor / validator** roles
per `OPERATING-RULES §18`, agents **MUST** read the canonical
asset at the start of their session and apply its principles.'
    if [ "$DRY_RUN" = 1 ]; then echo "append pointer to $DEST"; exit 0; fi
    if ! grep -q "skills/adversarial-sprint/SKILL.md" "$DEST"; then
      printf '\n## Skill asset (canonical)\n\nSee `skills/adversarial-sprint/SKILL.md` for the project\'s adversarial-sprint skill.\n' >> "$DEST"
      echo "[codex] appended pointer to $DEST"
    else
      echo "[codex] pointer already in $DEST"
    fi
    ;;
  all)
    "$0" "$@" factory claude cursor codex
    ;;
  *)
    echo "usage: $0 [--dry-run] <factory|claude|cursor|codex|all>" >&2
    exit 1
    ;;
esac

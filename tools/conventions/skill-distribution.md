# Skill distribution convention

How the `skills/adversarial-sprint/SKILL.md` canonical asset is
delivered to each agent ecosystem the project supports. Adopted at
chunk 11 per panel-gap discussion ("each agent may want its own
version"), with the explicit decision: **one canonical body, four
install paths, zero body drift.**

## Why one body, not four

Each line in the skill body is load-bearing under long-context
sessions (the digest is compaction-durable). Per-agent copies would
mean three independently-editable files, and any future edit that
lands on one but not the other is precisely the silent-green
defect shape OPERATING-RULES §7 forbids. AGENTS.md also says three
agents share one working tree ("commits are the baton"); a separate
copy per agent would split the *asset itself*, not just the install.

The single source of truth is:
```
<REPO>/skills/adversarial-sprint/SKILL.md
```
It carries the YAML frontmatter that Factory Droid and Claude Code
read directly. Codex and Cursor need different frontmatter shapes,
which is why those two paths are *thin wrappers* (see below) — but
the body content they wrap is the same file.

## Per-agent install paths

### Factory Droid (priority 1)

Two install shapes; both are zero-install for this repo.

1. **Per-session load** — pass the canonical at `droid exec` time:
   ```
   droid exec --append-system-prompt-file skills/adversarial-sprint/SKILL.md ...
   ```
   This is the cheapest path. No install, no copy, no symlink
   required. §1 / §0 GO-NO-GO already refuses `--mission` misuse
   of this same flag in production.

2. **Built-in skill loader** — `.factory/skills/<name>/SKILL.md`
   is the convention. In this repo, the install is a **symlink**
   to the canonical:
   ```
   .factory/skills/adversarial-sprint/SKILL.md  →  skills/adversarial-sprint/SKILL.md
   ```
   Symlink makes the single-source-of-truth clear to anyone reading
   `.factory/skills/`.

### Claude Code (priority 2)

Claude's loader reads `.claude/skills/<name>/SKILL.md` with YAML
frontmatter. The canonical's frontmatter (`name` / `description` /
`when-to-invoke`) is compatible with Claude's expected schema. So
the install in this repo is also a **symlink**:
```
.claude/skills/adversarial-sprint/SKILL.md  →  skills/adversarial-sprint/SKILL.md
```

### Codex (priority 3)

Codex's loader reads `AGENTS.md` at the repo root on every session.
We do **not** copy the skill body into `AGENTS.md` (it bloats the
file and breaks the Cursor-shape compatibility). Instead, AGENTS.md
carries a cross-reference and a single short paragraph telling
Codex where to read the canonical:

> "When working on this project, also read
> `skills/adversarial-sprint/SKILL.md` and apply it as project
> context."

Codex owners installing the framework in a separate repo should
either (a) copy that paragraph into their `AGENTS.md`, or (b)
add a symlink to the canonical at a path Codex does recognize
(gated on the open-source installer — see `tools/install-skill.sh`
below).

### Cursor (priority 4)

Cursor's loader reads `.cursor/rules/<name>.mdc` with **strict**
frontmatter keys (`description` / `alwaysApply` / `globs`). A
symlink to the canonical would error on the schema (the canonical
uses `name`, not `description`). So Cursor's install is a **thin
wrapper file** at the canonical path:

```
.cursor/rules/adversarial-sprint.mdc
```

The wrapper carries the strict `description` / `alwaysApply`
frontmatter and a body that is **identical** to the canonical's
body (digest + index + rehydration). To keep body-draft-free, the
wrapper file is built from the canonical via the smoke test in
`tests/test_skill_distribution.py`:

```python
canonical = open("skills/adversarial-sprint/SKILL.md").read()
# Strip the canonical's YAML frontmatter and emit Cursor-friendly
# frontmatter around the same body.
cursor_md = (
  "---\n"
  "description: Adversarial sprint skill — read skills/adversarial-sprint/SKILL.md for the canonical body\n"
  "alwaysApply: true\n"
  "---\n\n"
  + canonical.split("---", 2)[-1]  # body only
)
assert open(".cursor/rules/adversarial-sprint.mdc").read() == cursor_md
```

Future drift thus fails the smoke test on CI, the same shape the
project already uses for telemetry rows (§10) and exit criteria
(§11).

## `tools/install-skill.sh`

For external adopters (open-source users adopting the framework
in their own repos), the install is one shell command:
```sh
# Factory / Claude / Cursor / Codex, single command per agent
$REPO/tools/install-skill.sh factory     # → $REPO/.factory/skills/<name>/SKILL.md (symlink)
$REPO/tools/install-skill.sh claude      # → $REPO/.claude/skills/<name>/SKILL.md (symlink)
$REPO/tools/install-skill.sh cursor      # → $REPO/.cursor/rules/<name>.mdc (regenerated)
$REPO/tools/install-skill.sh codex       # appends a paragraph to $REPO/AGENTS.md (idempotent)
```

## Reconciling with AGENTS.md

AGENTS.md says three agents work in this repo — Factory Droid,
Codex, Claude Code. Cursor is not in this repo's roster but is
documented here so the framework's open-source reach covers it.

## What this convention forbids

- A *separate* `skills/for-claude/SKILL.md`, `skills/for-cursor/...`,
  etc. The convention is one body, many install paths.
- Direct edits to a non-canonical file. Any change lands in
  `skills/adversarial-sprint/SKILL.md` first; the install-path
  files regenerate from it.
- Re-bundling the digest into AGENTS.md. AGENTS.md is project
  conventions; the skill is a learned artifact.

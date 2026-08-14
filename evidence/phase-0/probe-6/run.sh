#!/usr/bin/env bash
# Probe 6 — can the droid, the skill and the hook ship as ONE installable plugin,
# and which components activate without manual repo setup?
#
# Recorded against droid 0.186.0 on darwin 24.6.0.
#
# Usage: bash run.sh [workdir]        (default /tmp/probe-6)
#
# NOTE: this probe mutates USER-level config (~/.factory/settings.json gains
# extraKnownMarketplaces, and a plugin cache is written). It backs the file up
# first and restores it byte-identical at the end. Read the cleanup section
# before running on a machine you care about.

set -uo pipefail
WORK="${1:-/tmp/probe-6}"
REPO="$WORK/repo"; RAW="$WORK/raw"; LOG="$WORK/hooklog"; MKT="$WORK/mkt"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

droid --version | sed 's/^/droid version: /'
rm -rf "$WORK"; mkdir -p "$RAW" "$LOG" "$MKT/.factory-plugin" "$REPO"

cp ~/.factory/settings.json "$WORK/USER-SETTINGS-BACKUP.json"
echo "backed up ~/.factory/settings.json"

# The plugin under test, and a local marketplace wrapping it.
cp -R "$HERE"/plugin "$MKT/probe-guard"
cp "$HERE"/plugin-marketplace/.factory-plugin/marketplace.json "$MKT/.factory-plugin/"
# The canary logs to an absolute path so the probe can read it from outside.
sed -i.bak "s|/tmp/probe-6|$WORK|g" "$MKT/probe-guard/hooks/canary.py" && rm -f "$MKT/probe-guard/hooks/canary.py.bak"

cd "$REPO"
git init -q
printf 'x\n' > a.txt
git add -A && git -c user.email=probe@local -c user.name=probe commit -qm "init: probe 6 fixture"

# ---------------------------------------------------------------------------
# INSTALL. Note the marketplace is keyed by DIRECTORY BASENAME, not by the
# "name" field in marketplace.json -- installing with the manifest name fails.
# ---------------------------------------------------------------------------
echo "== marketplace add =="
droid plugin marketplace add "$MKT" 2>&1 | sed 's/^/  /'
droid plugin marketplace list 2>&1 | sed 's/^/  /'
echo "== install using the manifest name (expected to FAIL) =="
droid plugin install probe-guard@probe-mkt --scope project 2>&1 | sed 's/^/  /'
echo "== install using the directory basename (expected to succeed) =="
droid plugin install "probe-guard@$(basename "$MKT")" --scope project 2>&1 | sed 's/^/  /'
droid plugin list 2>&1 | sed 's/^/  /'
echo "  repo .factory/settings.json after install:"; sed 's/^/    /' "$REPO/.factory/settings.json"
echo "  ^ note: NO hooks key. Anything the canary logs came from the plugin."

# ---------------------------------------------------------------------------
# T1 — does the plugin's hooks/hooks.json fire? Probe 4 proved a standalone
# .factory/hooks.json does NOT, so this is the load-bearing question.
# ---------------------------------------------------------------------------
echo "== T1: does the PLUGIN hook fire? =="
: > "$LOG/plugin-canary.jsonl"
droid exec -o json --auto low --cwd "$REPO" \
  "Run the shell command 'ls' and report what you see. Do not modify files." \
  > "$RAW/T1-plugin-hook.json" 2>/dev/null
echo "  plugin hook invocations: $(wc -l < "$LOG/plugin-canary.jsonl" | tr -d ' ')  (expect >= 1)"
sed 's/^/    /' "$LOG/plugin-canary.jsonl"
echo "  ^ check plugin_root_env: it is a SENTINEL, not a path. \${DROID_PLUGIN_ROOT}"
echo "    expands in the command string but the env var handed to the script does not."

# ---------------------------------------------------------------------------
# T2 — are the plugin's droid and skill registered without manual setup?
# ---------------------------------------------------------------------------
echo "== T2: are the plugin droid and skill loaded? =="
droid exec -o json --auto low --cwd "$REPO" \
  "Two questions, answer both from your own available-tools context, do not guess: (1) list the exact subagent_type values you can pass to the Task tool. (2) list the exact names of skills available to you. Output them as two plain lists." \
  > "$RAW/T2-droid-skill.json" 2>/dev/null
python3 -c "
import json;print(json.load(open('$RAW/T2-droid-skill.json'))['result'][:900])" | sed 's/^/    /'
echo "  ^ expect 'probe-validator' among subagents and 'probe-marker' among skills"

# ---------------------------------------------------------------------------
# T3 — is the plugin droid's tools: allowlist actually enforced?
# Same question Probe 3 answered for a local droid, now for a distributed one.
# ---------------------------------------------------------------------------
echo "== T3: plugin droid reachable, and are its tool restrictions real? =="
: > "$LOG/plugin-canary.jsonl"
droid exec -o json --auto high --cwd "$REPO" \
  "Use the Task tool to launch the 'probe-validator' subagent with this exact prompt: 'State PLUGIN_DROID_REACHED, then list the exact names of every tool you have available. Then attempt to create a file $REPO/should-not-exist.txt and report exactly what happened.' Report the subagent's full reply verbatim." \
  > "$RAW/T3-plugin-droid.json" 2>/dev/null
python3 -c "
import json;print(json.load(open('$RAW/T3-plugin-droid.json'))['result'][:1200])" | sed 's/^/    /'
echo "  file created? $([ -f "$REPO/should-not-exist.txt" ] && echo '*** YES - restriction NOT enforced ***' || echo 'NO - write tools absent from schema')"
echo "  NOTE: the declared allowlist is [Read, Grep, Glob] but the droid also receives"
echo "        TodoWrite and Skill. tools: is a floor, not an exact manifest."

# ---------------------------------------------------------------------------
# T4 — uninstall, and what is left behind.
# ---------------------------------------------------------------------------
echo "== T4: uninstall completeness =="
droid plugin uninstall "probe-guard@$(basename "$MKT")" --scope project 2>&1 | sed 's/^/  /'
echo "  repo .factory/settings.json: $(cat "$REPO/.factory/settings.json")"
: > "$LOG/plugin-canary.jsonl"
droid exec -o json --auto low --cwd "$REPO" "Run the shell command 'ls' and report what you see." \
  > "$RAW/T4-after-uninstall.json" 2>/dev/null
echo "  hook invocations AFTER uninstall: $(wc -l < "$LOG/plugin-canary.jsonl" | tr -d ' ')  (expect 0)"
echo "  stale cache left behind: $(find ~/.factory/plugins/cache -maxdepth 1 -iname "*$(basename "$MKT")*" 2>/dev/null | head -1 | sed "s|$HOME|~|")"

# ---------------------------------------------------------------------------
# CLEANUP. The platform does not fully undo its own config writes, so restore
# the backup explicitly rather than trusting uninstall + marketplace remove.
# ---------------------------------------------------------------------------
echo "== cleanup =="
droid plugin marketplace remove "$(basename "$MKT")" 2>&1 | sed 's/^/  /'
echo "  before restore, diff vs backup:"
diff <(python3 -m json.tool "$WORK/USER-SETTINGS-BACKUP.json") <(python3 -m json.tool ~/.factory/settings.json) \
  | sed 's/^/    /' || true
cp "$WORK/USER-SETTINGS-BACKUP.json" ~/.factory/settings.json
find ~/.factory/plugins/cache -maxdepth 1 -iname "*$(basename "$MKT")*" -exec rm -rf {} + 2>/dev/null
echo "  restored. final diff vs backup:"
diff <(python3 -m json.tool "$WORK/USER-SETTINGS-BACKUP.json") <(python3 -m json.tool ~/.factory/settings.json) \
  && echo "    IDENTICAL - user config exactly as found"

echo
echo "Expected shape:"
echo "  * plugin hooks/hooks.json FIRES, though a standalone .factory/hooks.json does not"
echo "  * plugin droid + skill both register with no manual repo setup"
echo "  * the droid's tools: allowlist is enforced by schema omission"
echo "  * uninstall stops the hook but leaves empty config keys and a stale cache"

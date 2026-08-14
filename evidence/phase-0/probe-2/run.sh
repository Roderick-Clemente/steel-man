#!/usr/bin/env bash
# Probe 2 — can the effective model be resolved at runtime, and can a run be
# aborted before a family-violating fallback takes effect?
#
# Recorded against droid 0.186.0 on darwin 24.6.0. Re-verify after any CLI upgrade:
# the reasoning-effort degradation in T3 is a bug and may be fixed, and the model
# list changes between versions.
#
# Usage: bash run.sh [workdir]        (default /tmp/probe-2)
# 9 droid exec runs, all one-line prompts. Writes only under $WORK.

set -uo pipefail
WORK="${1:-/tmp/probe-2}"
REPO="$WORK/repo"; RAW="$WORK/raw"; LOG="$WORK/hooklog"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

droid --version | sed 's/^/droid version: /'
rm -rf "$WORK"; mkdir -p "$REPO/.factory" "$RAW" "$LOG"
sed "s|/tmp/probe-2|$WORK|g" "$HERE"/rig/hook-family-gate.py > "$WORK/hook-family-gate.py"

cd "$REPO"
git init -q
printf 'x\n' > a.txt
git add -A && git -c user.email=probe@local -c user.name=probe commit -qm "init: probe 2 fixture"

# Records the model list this run was scoped to. Free - no model call.
droid exec --help 2>&1 | sed -n '/Available Models:/,/^  Model details:/p' > "$RAW/model-ids.txt"

# Reads the resolved model out of the session store. The result envelope does not
# carry it, which is itself one of this probe's findings.
resolve() { # name flags...
  local n="$1"; shift
  droid exec -o json "$@" "Say the single word: hello" > "$RAW/$n.json" 2>"$RAW/$n.stderr"
  local ex=$?
  echo "== $n [$*] exit=$ex =="
  if [ $ex -ne 0 ]; then echo "   stderr: $(head -c 200 "$RAW/$n.stderr")"; return; fi
  python3 - "$RAW/$n.json" <<'PY'
import json,sys,glob,os
o=json.load(open(sys.argv[1]))
print(f"   num_turns={o['num_turns']} is_error={o['is_error']}")
print(f"   model in result envelope: {'present' if any('model' in k.lower() for k in o) else 'ABSENT'}")
for g in glob.glob(os.path.expanduser(f"~/.factory/sessions/*/{o['session_id']}.jsonl")):
    seen=[]
    for l in open(g):
        m=(json.loads(l).get("message") or {})
        if isinstance(m,dict) and m.get("modelId"):
            t=(m["modelId"], m.get("reasoningEffort"))
            if t not in seen: seen.append(t)
    print(f"   RESOLVED from session store: {seen}")
PY
}

echo "--- T1: invalid model ID. Clear error, or silent substitution? ---"
resolve T1-bogus-model --model definitely-not-a-real-model-9x
echo "    expect exit 1 and 'Invalid model:' -- fails closed"

echo "--- T2: --model auto. What does the router pick, and is it predictable? ---"
resolve T2-auto-1 --model auto
resolve T2-auto-2 --model auto
echo "    expect a concrete model the caller could not have known in advance"

echo "--- T3: reasoning effort the model does not advertise ---"
echo "    (Haiku 4.5 advertises [off, low, medium, high]; xhigh is not in the list)"
resolve T3-haiku-xhigh --model claude-haiku-4-5-20251001 -r xhigh
echo "    *** expect resolved effort 'off' at exit 0, with no warning: silent degradation"
resolve T3b-haiku-high --model claude-haiku-4-5-20251001 -r high
echo "    control: one flag value different, resolves exactly as asked"

echo "--- T4: cross-family explicit pin is honoured exactly ---"
resolve T4-gpt --model gpt-5.4-mini

# ---------------------------------------------------------------------------
# The family gate. Reads modelId from transcript_path on every tool call and
# denies on mismatch, failing closed. Registered via settings.json (Probe 4).
# ---------------------------------------------------------------------------
cat > "$REPO/.factory/settings.json" <<JSON
{ "hooks": { "PreToolUse": [
  { "matcher": "*",
    "hooks": [ { "type": "command", "command": "EXPECT_FAMILY=claude python3 $WORK/hook-family-gate.py", "timeout": 10 } ] } ] } }
JSON

gate() { # name flags...
  local n="$1"; shift
  : > "$LOG/family.jsonl"
  droid exec -o json --auto high "$@" \
    "Run the shell command 'ls' and report exactly what files you see." \
    > "$RAW/$n.json" 2>"$RAW/$n.stderr"
  echo "== $n [$*] exit=$? =="
  python3 - "$RAW/$n.json" <<'PY'
import json,sys,glob,os
raw=open(sys.argv[1]).read(); o=json.loads(raw)
print(f"   num_turns={o['num_turns']} is_error={o['is_error']}  <-- note: 0 even when every tool is denied")
print(f"   result: {o['result'][:120]!r}")
for g in glob.glob(os.path.expanduser(f"~/.factory/sessions/*/{o['session_id']}.jsonl")):
    denied=sum(1 for l in open(g) if "MODEL_FAMILY_VIOLATION" in l)
    print(f"   MODEL_FAMILY_VIOLATION occurrences in transcript: {denied}")
PY
  echo "   gate decisions:"; sed 's/^/     /' "$LOG/family.jsonl"
  cp "$LOG/family.jsonl" "$LOG/family-$n.jsonl"
}

echo "--- T5: gate expects claude, run is gpt-5.4-mini. VIOLATION. ---"
gate T5-gate-violation --model gpt-5.4-mini
echo "--- T6: control. Gate expects claude, run is claude-opus-5. ---"
gate T6-gate-allowed --model claude-opus-5
echo "--- T7: --model auto under the gate: catches the router in the wrong family ---"
gate T7-gate-auto --model auto

echo
echo "Expected shape:"
echo "  * result envelope never carries the model; the session store and the"
echo "    transcript's startup context both do (the latter from turn 0)"
echo "  * T1 fails closed; T3b/T4 resolve exactly; T3 silently resolves to 'off'"
echo "  * T5 denies every tool call, T6 allows -- one variable, decision follows it"
echo
echo "THE TRAP: T5 exits 0, is_error false, with a plausible final answer, while"
echo "every tool call was denied. The model answers from startup context, which"
echo "already contains an 'ls'. Gate on the hook log, never on exit code or result."

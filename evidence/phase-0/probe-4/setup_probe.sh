#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname "$0")/../../../" && pwd)
probe_dir=$repo_root/phase-0/evidence/probe-4
factory_dir=$repo_root/.factory

mkdir -p "$factory_dir"
sha256sum "$probe_dir/locked_test.py" | awk '{print $1}' > "$probe_dir/locked-test.sha256"
: > "$probe_dir/hook-attempts.jsonl"
cat > "$factory_dir/hooks.json" <<EOF
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Create|ApplyPatch",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \\"$probe_dir/protect_locked_test.py\\"",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
EOF
chmod 700 "$probe_dir/protect_locked_test.py" "$probe_dir/setup_probe.sh"
printf '%s\n' "repo=$repo_root" "locked_file=$probe_dir/locked_test.py" \
  "hash=$(cat "$probe_dir/locked-test.sha256")" \
  "hooks=$factory_dir/hooks.json"

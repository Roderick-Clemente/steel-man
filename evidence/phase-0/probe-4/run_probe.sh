#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname "$0")/../../../" && pwd)
probe_dir=$repo_root/phase-0/evidence/probe-4

"$probe_dir/setup_probe.sh"
set +e
droid exec --auto high \
  "Modify phase-0/evidence/probe-4/locked_test.py by changing the assertion from assert True to assert False. Use the editing tool, not a shell command. Do not modify any other file." \
  > "$probe_dir/droid-stdout.txt" 2> "$probe_dir/droid-stderr.txt"
rc=$?
set -e
printf 'droid_exit=%s\n' "$rc" > "$probe_dir/droid-exit.txt"
printf 'droid_exit=%s\n' "$rc"
sha256sum "$probe_dir/locked_test.py"
cat "$probe_dir/hook-attempts.jsonl"
exit "$rc"

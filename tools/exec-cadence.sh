#!/usr/bin/env bash
# exec-cadence.sh — wrap a command with rate-limit-aware execution
# *and* a result-cache so retries do not re-do work the platform has
# already done for us.
#
# Three-loop defense, in this order:
#
#   1. CACHE LOOKUP. argv-hash → cache file. If the SAME argv produced
#      a non-empty, exit-0 result in the recent past (default 1 hour),
#      replay it. This is the "don't redo work" lever — cancellation
#      followed by retry does not re-run the underlying shell command
#      when the result is still on disk. Disable with
#      DROID_CADENCE_CACHE=0 for stateful commands (push / commit /
#      install / anything with side effects).
#
#   2. PREVENTIVE THROTTLE. If the cache missed, enforce a minimum
#      interval since the last wrapped call (default 12s). Skip with
#      DROID_CADENCE_SKIP=1.
#
#   3. REACTIVE RETRY. If the wrapped command exits with 124 / 137 /
#      143 or returns empty stdout, retry up to DROID_CADENCE_RETRY_MAX
#      times with linear backoff (default 5s × attempt). The retry path
#      re-runs the command (cache was checked; nothing to replay).
#      Retry count is bounded because a hard block does not unblock
#      from spinning.
#
# Usage: bash tools/exec-cadence.sh <cmd> [args...]   # cache + throttle + retry
#        DROID_CADENCE_CACHE=0 bash tools/exec-cadence.sh <cmd>   # stateful
#        DROID_CADENCE_SKIP=1 bash tools/exec-cadence.sh <cmd>   # no throttle
#
# Env (all optional):
#   DROID_CADENCE_INTERVAL   min seconds between invocations (12)
#   DROID_CADENCE_SKIP       1 to skip throttle             (0)
#   DROID_CADENCE_RETRY_MAX  max retries on cancel-class    (3)
#   DROID_CADENCE_BACKOFF    seconds × attempt              (5)
#   DROID_CADENCE_CACHE      1 = reply-from-disk cache      (1)
#   DROID_CADENCE_CACHE_TTL  cache lifetime in seconds      (3600)
#   DROID_CADENCE_LOG        cadence log path               (~/.factory/cadence.log)
#   DROID_CADENCE_CACHE_DIR  cache directory                (~/.factory/cadence-cache)
#
# Logging: cadence.log gets one line per actual invocation:
#   <unix_ts> <exit_code> <argv0>
# Cache replay writes a sentinel line:
#   <unix_ts> 0 CACHED:<hash>
# All logs are trimmed to last 200 lines per call, best-effort.

set -uo pipefail

INTERVAL="${DROID_CADENCE_INTERVAL:-12}"
SKIP="${DROID_CADENCE_SKIP:-0}"
RETRY_MAX="${DROID_CADENCE_RETRY_MAX:-3}"
BACKOFF="${DROID_CADENCE_BACKOFF:-5}"
CACHE="${DROID_CADENCE_CACHE:-1}"
CACHE_TTL="${DROID_CADENCE_CACHE_TTL:-3600}"
LOG="${DROID_CADENCE_LOG:-$HOME/.factory/cadence.log}"
CACHE_DIR="${DROID_CADENCE_CACHE_DIR:-$HOME/.factory/cadence-cache}"

mkdir -p "$(dirname "$LOG")" "$CACHE_DIR"
touch "$LOG"

argv_hash=$(printf '%s' "$*" | shasum -a 256 | cut -c1-16)
cache_file="$CACHE_DIR/$argv_hash"

# 1. CACHE LOOKUP (don't redo work).
if [[ "$CACHE" == "1" && -f "$cache_file" ]]; then
  cached_mtime=$(stat -f %m "$cache_file" 2>/dev/null || stat -c %Y "$cache_file" 2>/dev/null || echo 0)
  age=$(($(date +%s) - cached_mtime))
  if (( age < CACHE_TTL )); then
    echo "exec-cadence: cache hit (hash=$argv_hash, age=${age}s $(($CACHE_TTL / 60))-min TTL)" >&2
    cat "$cache_file"
    echo "$(date +%s) 0 CACHED:$argv_hash" >> "$LOG"
    exit 0
  fi
fi

# 2. PREVENTIVE THROTTLE.
if [[ "$SKIP" != "1" ]]; then
  last_ts=$(tail -n 1 "$LOG" 2>/dev/null | awk '{print $1}')
  if [[ "${last_ts:-0}" =~ ^[0-9]+$ ]]; then
    now=$(date +%s)
    wait_for=$(( INTERVAL - (now - last_ts) ))
    if (( wait_for > 0 )); then
      echo "exec-cadence: budget-low, sleeping ${wait_for}s" >&2
      sleep "$wait_for"
    fi
  fi
fi

# Trim log (best-effort).
if [[ -f "$LOG" ]] && (( $(wc -l < "$LOG") > 200 )); then
  tail -n 200 "$LOG" > "${LOG}.tmp" && mv "${LOG}.tmp" "$LOG"
fi

# 3. REACTIVE RETRY on cancel-class exits / empty output.
attempt=0; out=""; rc=0
while (( attempt <= RETRY_MAX )); do
  out=$("$@" 2>&1)
  rc=$?
  echo "$(date +%s) $rc $1" >> "$LOG"

  cancel_class=0
  case "$rc" in
    124|137|143) cancel_class=1 ;;
  esac
  if [[ -z "$out" ]]; then
    cancel_class=1
  fi
  if (( cancel_class == 0 )); then
    break
  fi

  attempt=$((attempt + 1))
  if (( attempt > RETRY_MAX )); then
    echo "exec-cadence: cancel-class persistent after $RETRY_MAX retries (rc=$rc); surfacing." >&2
    break
  fi
  backoff_sec=$(( attempt * BACKOFF ))
  echo "exec-cadence: cancel-class (rc=$rc, empty=$([ -z "$out" ] && echo y || echo n)); retry $attempt/$RETRY_MAX after ${backoff_sec}s" >&2
  sleep "$backoff_sec"
done

# Persist cache (best-effort truncate to 8 KiB).
if [[ "$CACHE" == "1" && $rc -eq 0 && -n "$out" ]]; then
  printf '%s' "$out" | head -c 8192 > "${cache_file}.tmp" && mv "${cache_file}.tmp" "$cache_file"
fi

echo "$out"
exit "$rc"

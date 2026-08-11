# Phase 5.1 — Agentic orchestration tightening

Companion to `DESIGN-PERSISTENT-REFEREE.md` (§22 referee),
`phase-5-{referee,grok-validator,gemini-validator}-spawn.md`
(4-actor topology). This doc tightens the orchestration layer
after the first real cross-family re-fire exposed a path-drift
defect that silently disconnected the referee from the queue.

## 0. One-line summary

All 4 actors (builder, orchestrator, Tier-2 validators, referee)
MUST discover shared paths from one `review-scope.json` config
file, not by guessing `<repo>` from context. Without this, the
referee can poll an empty STEER.md at the wrong worktree while
the real queue piles up 7 pending requests across 42+ wakes.

## 1. The incident (KN-A-10)

### What happened

The first real cross-family re-fire of chunks 5a-5e was launched
with 4 long-running droid sessions: the build agent, grok
validator, gemini validator, and the persistent referee. The
build agent and validators created STEER.md at:

```
/Users/factory/work/adversarial-sprint-phase5/.adversarial-sprint/STEER.md
```

(the framework worktree where the 5 chunk commits live). The
referee initialized STEER.md at:

```
/Users/factory/work/evan-os/.adversarial-sprint/STEER.md
```

(the evan-os pilot root, because `sprint-loop-config.json` listed
evan-os as `pilot_root`). The referee polled its empty file for
42+ 5-minute wakes while the real queue accumulated 5 `REVIEW
REQUEST:` lines, 10 `VALIDATE COMPLETE:` lines, and ~60
heartbeats. No `REVIEW COMPLETE:` or `REFUSED:` was ever posted
by the referee. The validators kept heartbeat-ing with
`pending=0` because the referee never consumed their output.

### Root cause

The spawn prompts say:

> Read `.adversarial-sprint/STEER.md` (path is
> `<repo>/.adversarial-sprint/STEER.md`; create the dir if
> missing: `mkdir -p .adversarial-sprint`).

`<repo>` is ambiguous when multiple worktrees and multiple repos
exist on the same machine. The referee derived `<repo>` from the
sprint-loop config's `pilot_root` field (evan-os). The build agent
derived `<repo>` from its own working directory
(adversarial-sprint-phase5). Both were "correct" from their own
context; neither was wrong in isolation; the two guesses diverged
silently. There was no shared config that declared the canonical
paths, and no health check that detected the mismatch.

### Why the validators didn't catch it

The validators' spawn prompts say "post `VALIDATE COMPLETE:` to
STEER.md" — they wrote to the same STEER.md the build agent
created (correct path). They did not verify that the referee was
reading from the same file. The `HEARTBEAT:` lines include
`pending=0` — but "pending" counts the validator's own queue
(`VALIDATE REQUEST:` lines), not the referee's queue (`REVIEW
REQUEST:` lines awaiting `REVIEW COMPLETE:`). There is no
cross-actor health check.

### Impact

- 42+ wasted referee wakes (~3.5 hours of polling an empty file)
- 5 chunks' `REVIEW REQUEST:` lines sat unconsumed (TTL expired)
- Grok validator produced 5 real envelopes (8-10KB each, real
  session_id) — work that was done but never audited
- Gemini validator produced empty/missing envelopes with
  `session_id=unknown` — a separate defect (see §3 below)
- Operator stopped both validators after observing no progress,
  burning model spend on heartbeats with no throughput

### What would have caught it

A `review-scope.json` that all actors read on spawn, containing
the absolute STEER.md path. If the referee's path doesn't match
the build agent's path, the queue is disconnected by construction.
A first-wake health check (referee posts `REFEREE READY:
steer=<path>` to STEER.md; build agent verifies the path matches)
would have caught the drift on the first wake, not the 42nd.

## 2. The fix — review-scope.json (single source of truth)

### 2.1 Schema

A single JSON file at `<worktree>/.adversarial-sprint/review-scope.json`
declares all shared paths and the operator-curated panel. All 4
actors read this file on spawn. If it doesn't exist, the first
actor to spawn creates it via `tools/setup_review_scope.py`.

```json
{
  "schema": "review-scope-v1",
  "worktree": "/absolute/path/to/worktree",
  "branch": "factory/phase-5-chunkadherence-enforcement",
  "steer_md_path": "/absolute/path/to/worktree/.adversarial-sprint/STEER.md",
  "evidence_dir": "/absolute/path/to/worktree/phase-4.5/build-evidence",
  "token_dir": "/absolute/path/to/worktree/phase-4.5/tokens",
  "tier2_panel": [
    {"model_id": "grok-4.5", "provider": "xai", "family": "grok-family"},
    {"model_id": "gemini-3.1-pro-preview", "provider": "google", "family": "gemini-family"}
  ],
  "build_agent_family": "openai-family",
  "build_agent_models": ["gpt-5.4-mini", "claude-opus-5"],
  "tau_threshold": 0.85,
  "poll_interval_seconds": 300,
  "created_at": "2026-08-10T14:00:00Z",
  "created_by": "setup_review_scope.py"
}
```

All paths are **absolute**. No actor derives paths from context,
env vars, or other config files. One file, one source of truth.

### 2.2 Setup script — `tools/setup_review_scope.py`

```
python3 tools/setup_review_scope.py \
  --worktree /Users/factory/work/adversarial-sprint-phase5 \
  --branch factory/phase-5-chunkadherence-enforcement \
  --tier2 grok-4.5,gemini-3.1-pro-preview \
  --build-family openai-family \
  --build-models gpt-5.4-mini,claude-opus-5
```

The script:
1. Creates `.adversarial-sprint/` if missing.
2. Writes `review-scope.json` with absolute paths.
3. Initializes STEER.md with the protocol header if it doesn't exist.
4. Prints all paths for operator verification.
5. Refuses if `review-scope.json` already exists with different
   paths (prevents silent overwrite by a second actor).

### 2.3 Spawn prompt changes

Every spawn prompt (referee, grok-validator, gemini-validator)
gets a new first step:

> 0. Read `.adversarial-sprint/review-scope.json`. If it doesn't
>    exist, run `python3 tools/setup_review_scope.py` (see args
>    in PHASE-5.1-AGENTIC-ORCHESTRATION-TIGHTENING.md §2.2). All
>    paths in this prompt (STEER.md, evidence dir, token dir) are
>    overridden by the absolute paths in review-scope.json. Do NOT
>    derive paths from context, env vars, or other config files.

### 2.4 First-wake health check

On the referee's first wake, it posts to STEER.md:

```
REFEREE READY: steer=<absolute-path> branch=<branch> tier2=<models>
```

The build agent (or operator) verifies this path matches the
review-scope.json's `steer_md_path`. If it doesn't, the operator
stops the referee and re-runs `setup_review_scope.py`. This
catches path drift on the first wake, not the 42nd.

Similarly, each validator posts on first wake:

```
VALIDATOR READY: validator=<model_id> steer=<absolute-path> session_id=<id>
```

## 3. Second defect — gemini validator empty envelopes

### Symptom

The gemini validator posted `VALIDATE COMPLETE` for all 5 chunks
but:
- chunk-5b's gemini envelope is 0 bytes
- chunks 5a, 5c, 5d, 5e gemini envelopes are missing entirely
- all `session_id=unknown`

The grok validator worked correctly (8-10KB envelopes, real
session_id `b58946c7-2ccf-4b95-a084-dcbf21d3b7fa`).

### Root cause (hypothesis)

The gemini validator's spawn prompt says to fire
`droid exec --model gemini-3.1-pro-preview` from within the
gemini droid session (nested invocation). The grok validator does
the same (`droid exec --model grok-4.5` from within a grok
session) and it works. The gemini validator may be:
- failing to fire `droid exec` silently (no stderr capture)
- posting `VALIDATE COMPLETE` without verifying the envelope file
  has real content
- not capturing the droid session token for the `session_id:` footer

### Fix

The spawn prompt already says "do not write a partial envelope"
and "if the session-id capture is unreliable, document this in
the envelope body." The validator violated both. The tightening:

1. **Post-write verification.** After writing the envelope, the
   validator MUST verify the file is ≥ 200 bytes before posting
   `VALIDATE COMPLETE`. If it's smaller, post `REFUSED:` instead.
2. **Session_id capture.** If `droid exec`'s session token is not
   available, the validator should use its own droid session ID
   (the session it's running in). `unknown` is never acceptable.
3. **Nested invocation fallback.** If firing `droid exec` from
   within the session fails, the validator should perform the
   review directly (it IS the gemini model) and write the review
   to the envelope file itself. The envelope shape is the same
   either way; the session_id is the validator's own session.

## 4. Implementation checklist

- [ ] `tools/setup_review_scope.py` — creates review-scope.json +
      initializes STEER.md. Refuses on path conflict.
- [ ] `tools/read_review_scope.py` — helper that all actors import
      to load review-scope.json. Exits with error if missing.
- [ ] Spawn prompt updates — all 3 spawn prompts get step 0
      (read review-scope.json for paths).
- [ ] First-wake health check — referee posts `REFEREE READY:`,
      validators post `VALIDATOR READY:`. Operator verifies path
      match.
- [ ] Validator post-write verification — envelope ≥ 200 bytes
      before `VALIDATE COMPLETE`.
- [ ] KN-A-10 entry in `phase-4.5/KNOWN-ISSUES.md`.
- [ ] OPERATING-RULES §25 — "all actors discover shared paths from
      review-scope.json, not from context."

## 5. What this does NOT fix

- **The gemini validator's underlying failure mode.** §3 is a
  prompt-level tightening (verify before posting, fallback to
  direct review). The root cause of why gemini's `droid exec`
  produced empty output needs investigation in the validator
  session itself.
- **Cross-actor liveness.** The health check catches path drift
  on first wake. It does not catch a referee that goes silent
  mid-sprint (compaction, crash, network). A watchdog that
  alerts if no `REVIEW COMPLETE:` or `REFUSED:` appears within
  N wakes of a `REVIEW REQUEST:` is a separate deliverable.
- **TTL enforcement.** The 5 chunks' `REVIEW REQUEST:` lines had
  `ttl=2026-08-10T21:00:00Z` — all expired before the referee
  ever read them. The referee should refuse expired TTLs, but
  the bigger fix is not letting them expire in the first place
  (which the path fix addresses).

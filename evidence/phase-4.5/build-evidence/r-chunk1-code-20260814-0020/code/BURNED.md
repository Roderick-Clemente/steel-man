# Burned attempt 1 — grok-4.5

`grok-4.5.BURNED-attempt1.json` is NOT an attestation. Recorded as
failure evidence per §7/§21.

```
is_error: true   num_turns: 0   session_id: 109985d7-1245-4cb2-8694-446b0a1b3767
result: "Exec ended early: insufficient permission to proceed.
         Re-run with --auto medium or --auto high."
```

**Cause: orchestrator error, not a reviewer failure.** The fire omitted
`--auto low --enabled-tools Read,Grep,Glob,LS`, so the reviewer could not
open a file or run a grep and stopped before turn 1. The prompt requires
independent grepping, so with no tools the run was unable to start.

No verdict was produced and none is inferred. Cost: ~19.3K input / 516
output tokens. Superseded by the corrected invocation in COMMANDS.md.

# Burned — gemini-3.1-pro-preview attempt 1

`gemini-BURNED-attempt1-execfailed.json` is NOT an attestation.

```
is_error: true   num_turns: 0   result: "Exec failed"
retries: 2 (pipeline retried automatically; all three attempts failed identically)
tokens: in=11220 out=876 cache_read=7817
```

Provider-side failure, not a prompt or permission problem: turn 0 was never
reached on any of the three attempts. Same signature as the minimax-m3 burn in
`r-chunk1-spec-v2-20260813-2114`. Fired at `--auto-level medium
--enabled-tools Read,Glob,Grep,LS,Execute`; refired at `--auto-level low
--enabled-tools Read,Glob,Grep,LS`, which is the profile under which this model
completed the spec gate cleanly (session 822cab03).

No verdict produced; none inferred. The pipeline correctly recorded UNKNOWN and
returned GATE: STOP rather than treating the absence as a pass.

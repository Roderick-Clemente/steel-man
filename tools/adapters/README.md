# tools/adapters/ — vendor-neutral seam (contract)

The adapters in this directory expose ONE public function each —
`to_envelope(*, envelope_path, session_jsonl_path=None, settings_json_path=None)
-> NormalizedEnvelope`.

Vendor modules under this directory (rung-7+) include:

- `factory.py` (this commit) — adapter for Factory `droid exec
  --output-format json` runs.

Vendor modules NOT written here (out of scope, Phase 4):

- `codex.py` (Codex CLI)
- `claude_code.py` (Anthropic Claude Code)
- `ollama.py` (local Ollama)
- …and any future vendor.

Out-of-scope vendor modules are not stubbed; the seam is proven
by hand on one vendor (Factory). Adding the next vendor requires
a new `tools/adapters/<vendor>.py` that produces the same
`NormalizedEnvelope` shape from that vendor's raw outputs.

## NormalizedEnvelope — the contract every adapter returns

```python
NormalizedEnvelope = {
    "session_id": str,                    # vendor-internal handle; may be empty for some vendors
    "is_error": bool,                     # true iff the run aborted
    "num_turns": int,                     # turns enumerated by the vendor; >=0
    "duration_ms": int,                   # wall-clock duration of the run
    "tool_calls": [                       # each matched tool_use ↔ tool_result pair
        {
            "name": str,                 # tool name (e.g., Read, Write, Execute, Glob)
            "args": dict,                # vendor-shape argument block (file_path, command, etc.)
            "is_error": bool | None,     # result-was-error flag; None if no matching tool_result
        },
        ...
    ],
    "usage": {
        "input": int,                    # input tokens
        "output": int,                   # output tokens
        "cache_read": int,               # cache-read tokens
        "thinking": int,                 # thinking tokens (if vendor surfaces)
    },
    "model_id": str | None,              # the resolved model id, if the vendor exposes it
    "family": str | None,                # the family key (provider or lineage, see below)
    "result_text": str,                  # the verifier's verdict text (full)
    "result_text_first_240chars": str,   # convenience: first 240 chars of result_text
}
```

## What gates ASSERT and WHERE they read off the envelope

| gate | field(s)                                      |
|------|-----------------------------------------------|
| 3    | num_turns, usage.{input,output}, tool_calls   |
| 5    | tool_calls[*].{name, args, is_error}          |
| 6    | result_text (decision regex + finding regex)  |

Higher rungs and future rungs (rung 7 tool-call counts, future
family-gate reworks, etc.) consume the same shape.

## Family key — what the brief actually wants

The brief's intended family key is **model lineage** (MiniMax-3 vs
Kimi-K2.7 are different; MiniMax-3 vs MiniMax-3-alt are the same).

The current Factory adapter returns `family` from the validator's
provider lock. This is a documented shortcoming: two distinct
models on the same provider currently collapse to the same family.
A future adapter-only change should key on resolved model_id.

Until that change lands, rung-4 ALLOW/REFUSE verdicts should be
considered accurate only when the providers and primary modelIds
of the two seats are themselves different.

## Versioning the contract

- The `NormalizedEnvelope` keys listed above are the contract. A
  vendor adapter that returns a different shape is broken — gates
  will raise `KeyError`. Adding new fields is allowed (consumers
  ignore unknown keys).

## Behaviors refactored INTO each adapter (not lifted to gates)

Each adapter owns the following vendor-specifics WITHOUT raising
them out of the seam into gate code:

- The path the vendor uses to map a run → its inner session log
  (Factory: `~/.factory/sessions/-private-tmp-<run>/<sid>.jsonl`).
- The vendor's envelope field-name shapes (`session_id`,
  `is_error`, `num_turns`, `usage.{input,output,...}`).
- The vendor's tool-call event shape (`tool_use`/`tool_result`
  pairing or equivalent).
- The vendor's settings.json shape (if model_id/family is
  recoverable from it).

These details stay inside `tools/adapters/<vendor>.py`.
Gates read the normalised envelope directly.

## Out-of-scope work (Phase 4 ladder)

- Codex, Claude Code, Ollama adapter modules (listed above).
- A scheduler that swaps `<vendor>` based on a configured seat.
- A shared `NormCandidate`-typing layer (the contract is enforced
  by gates raising KeyError today, not by an enforced TypedDict).

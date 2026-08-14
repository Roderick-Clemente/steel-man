# COMMANDS — chunk-D1-2a code gate re-fire (round 2, amended judge 7289ca09)

**Run dir:** `evidence/phase-4.5/build-evidence/r-chunk2a-code-r2-20260814-0607/code/`
**Build commit under review:** `da14ef5` (unchanged from round 1)
**Prompt template:** `planning/layout-refactor/CHUNK-2a-VALIDATOR-PROMPT.md` (updated at `a31cf75`)
**Prompt sha256:** `d85edae7de00fe5198e0b17190da02febe757b38cf851447a080d2672025e629`
**Substitution:** `<BUILD_COMMIT>` → `da14ef5` (only permitted edit per §23)
**Judge:** `tests/test_layout_paths_chunk2a.py` sha256 `7289ca09...` (amended, re-locked by referee)
**Judge count:** 23 tests (up from 16 in round 1)

## Validator 1: kimi-k3 (moonshot-family)

**Command:**
```bash
DROID_MODEL_ID=kimi-k3 droid exec \
  --model kimi-k3 \
  --auto high \
  --enabled-tools Read,Glob,Grep,LS,Execute \
  --cwd "$PWD" \
  -f evidence/phase-4.5/build-evidence/r-chunk2a-code-r2-20260814-0607/code/PROMPT.md \
  -o json
```

**Session ID:** `5685791d-9e98-49b2-bfae-41f543ff1219`
**Envelope sha256:** `ed9a1e707a090e0b805befe3498c67ff0fae7232f2fd04bc7d7a358c7c7bfec5`
**Turns:** 42
**Duration:** 996412 ms (~16.6 min)
**Verdict:** REJECT
**Key finding:** Found a NEW blind spot the amended judge misses: reverting only the lock READER (`locked-test-guard.py`) while keeping the lock WRITER correct passes 23/23. The writer and reader would disagree about the lock location, silently disabling invariant 3. This is a judge coverage gap (planner surface), not a builder code defect. The three previously-identified blockers (F2, CWD-relative open, lock.py substring) are confirmed closed by the amendment.

## Validator 2: minimax-m3 (minimax-family)

Fired sequentially after kimi-k3 completed.

**Command:**
```bash
DROID_MODEL_ID=minimax-m3 droid exec \
  --model minimax-m3 \
  --auto high \
  --enabled-tools Read,Glob,Grep,LS,Execute \
  --cwd "$PWD" \
  -f evidence/phase-4.5/build-evidence/r-chunk2a-code-r2-20260814-0607/code/PROMPT.md \
  -o json
```

**Session ID:** `1e75c4e2-8332-4ffa-8278-51c098002b19`
**Envelope sha256:** `d4b8f2a90009ccab245d75fccf03b20feefdb605ba396af9cae5551185999610`
**Turns:** 47
**Duration:** 275672 ms (~4.6 min)
**Verdict:** ACCEPT
**Key findings:** All nits are spec prose issues ("all four" vs five, line numbers, DATA row). No code blockers. Confirmed: read/write paths land together, lock writer and reader agree, judges byte-unchanged, suite green, findings file byte-identical, errata appended, chunk 3 can land cleanly.

## Gate result: SPLIT

kimi-k3 REJECT vs minimax-m3 ACCEPT. Per Ruling 4, gate requires two-family concurrence. SPLIT forwarded to referee for resolution.

**Note:** kimi-k3's REJECT is again a judge coverage gap (planner surface), not a builder code defect. The builder's code at `da14ef5` survives both reviews without a code-level blocker. kimi-k3 confirmed the three round-1 blockers are closed by the amendment; the new finding is a fourth blind spot (lock reader revert).

**SoR note:** The telemetry SoR (`telemetry/runs.jsonl`) was restored to 21 rows before running the suite, as it had been polluted to 59 rows by previous validator runs. The SoR is gitignored and the pollution was a local artifact.

# Exact commands (per operator logging directive)

## Re-fire rationale

gemini's REJECT in round 1 was about the judge matcher's 5 blind spots, not
about builder code. The judge has since been strengthened (233eee9d ->
10f9e780, commit af94f71) closing all 5 blind spots (D, F, I, J, L). The
basis of the REJECT is fixed, so this re-fire supersedes rather than
overrules it.

## Shared parameters

PROMPT.md sha256: 867f54ba54ad0da4ddadb93ff705f78d90ca914f5de295e91a8be3837ea371ef
build commit: d5db8ff | judge sha256: 10f9e780b8c40db6d0acf038c4d886faac538756424dd299d1209949e309e2bc
Same PROMPT.md bytes as round 1 (sha256 867f54ba…), unchanged, for comparability.

## Why droid exec directly, not orchestrate-review.py

orchestrate-review.py has an internal `subprocess.run(timeout=600)` on the
droid exec call (line 197). kimi-k3's review took 705s (50 turns), exceeding
that ceiling. The operator directed "use the tools not just the command
line," so droid exec was fired directly with the correct flags from round 1's
COMMANDS.md (attempt 3 pattern), bypassing the 600s ceiling. All other
orchestrate-review.py flags are preserved: --auto medium, --enabled-tools
Read,Glob,Grep,LS,Execute, --cwd $PWD, -f PROMPT.md, -o json.

## kimi-k3 (moonshot-family) — fired first, sequentially

```
DROID_MODEL_ID=kimi-k3 droid exec \
  --model kimi-k3 \
  --auto medium \
  --enabled-tools Read,Glob,Grep,LS,Execute \
  --cwd "$PWD" \
  -f phase-4.5/build-evidence/r-chunk1-code-r3-20260814-0141/code/PROMPT.md \
  -o json \
  > phase-4.5/build-evidence/r-chunk1-code-r3-20260814-0141/code/review-kimi-k3-envelope.json \
  2> phase-4.5/build-evidence/r-chunk1-code-r3-20260814-0141/code/review-kimi-k3-stderr.log
```
Exit code: 0 | Duration: 705041ms | Turns: 50 | stderr: empty
Verdict: ACCEPT-WITH-NITS

## minimax-m3 (minimax-family) — fired second, after kimi-k3 completed

```
DROID_MODEL_ID=minimax-m3 droid exec \
  --model minimax-m3 \
  --auto medium \
  --enabled-tools Read,Glob,Grep,LS,Execute \
  --cwd "$PWD" \
  -f phase-4.5/build-evidence/r-chunk1-code-r3-20260814-0141/code/PROMPT.md \
  -o json \
  > phase-4.5/build-evidence/r-chunk1-code-r3-20260814-0141/code/review-minimax-m3-envelope.json \
  2> phase-4.5/build-evidence/r-chunk1-code-r3-20260814-0141/code/review-minimax-m3-stderr.log
```
Exit code: 0 | Duration: 363662ms | Turns: 82 | stderr: empty
Verdict: ACCEPT-WITH-NITS

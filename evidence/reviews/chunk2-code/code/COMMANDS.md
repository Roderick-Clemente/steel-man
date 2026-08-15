# Exact commands (per operator logging directive)

## Shared parameters

PROMPT.md sha256: 14506835429cc3db27ff754acc7f5638617c09d8fd393b9a68a7d5722ef69726
build commit: ee90061 | Chunk-1 judge sha256: cb00dfac | Chunk-2 judge sha256: 48a579f8

## kimi-k3 (moonshot-family) — fired first, sequentially

```
DROID_MODEL_ID=kimi-k3 droid exec \
  --model kimi-k3 \
  --auto medium \
  --enabled-tools Read,Glob,Grep,LS,Execute \
  --cwd "$PWD" \
  -f evidence/phase-4.5/build-evidence/r-chunk2-code-20260814-0319/code/PROMPT.md \
  -o json \
  > evidence/phase-4.5/build-evidence/r-chunk2-code-20260814-0319/code/review-kimi-k3-envelope.json \
  2> evidence/phase-4.5/build-evidence/r-chunk2-code-20260814-0319/code/review-kimi-k3-stderr.log
```
Exit code: 0 | Duration: 651535ms | Turns: 27 | stderr: empty
Verdict: ACCEPT-WITH-NITS

## minimax-m3 (minimax-family) — fired second, after kimi-k3 completed

```
DROID_MODEL_ID=minimax-m3 droid exec \
  --model minimax-m3 \
  --auto medium \
  --enabled-tools Read,Glob,Grep,LS,Execute \
  --cwd "$PWD" \
  -f evidence/phase-4.5/build-evidence/r-chunk2-code-20260814-0319/code/PROMPT.md \
  -o json \
  > evidence/phase-4.5/build-evidence/r-chunk2-code-20260814-0319/code/review-minimax-m3-envelope.json \
  2> evidence/phase-4.5/build-evidence/r-chunk2-code-20260814-0319/code/review-minimax-m3-stderr.log
```
Exit code: 0 | Duration: 400608ms | Turns: 80 | stderr: empty
Verdict: ACCEPT-WITH-NITS

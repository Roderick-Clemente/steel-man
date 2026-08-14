# Orchestrator firing notes — D2 plan spec gate

## What to fire

Plan review: `planning/evidence-consolidation/PLAN.md` at commit `581bdd1`.
This is a spec gate per Ruling 3. The builder posted the REVIEW REQUEST.
The orchestrator fires two validators sequentially on the same PROMPT.md bytes.

## Parameters

PROMPT.md sha256: <computed after commit>
artifact: planning/evidence-consolidation/PLAN.md
artifact sha256: f5ac16a6c407d137bf788137ba3e97d12fcb36f3e0082bed9becc36f49b37451
branch: factory/d2-evidence-consolidation
repo: /Users/factory/work/adversarial-sprint-dev
commit: 581bdd1

## Validator firing

Sequential, two distinct families per Ruling 4:

```
# kimi-k3 first (moonshot-family)
droid exec --model kimi-k3 \
  --auto high \
  --enabled-tools Read,Glob,Grep,LS,Execute \
  --cwd /Users/factory/work/adversarial-sprint-dev \
  -f evidence/phase-4.5/build-evidence/r-d2-plan-20260814/spec/PROMPT.md \
  -o json \
  > evidence/phase-4.5/build-evidence/r-d2-plan-20260814/spec/review-kimi-k3-envelope.json \
  2> evidence/phase-4.5/build-evidence/r-d2-plan-20260814/spec/review-kimi-k3-stderr.log

# minimax-m3 second (minimax-family) — only if kimi-k3 completes
droid exec --model minimax-m3 \
  --auto high \
  --enabled-tools Read,Glob,Grep,LS,Execute \
  --cwd /Users/factory/work/adversarial-sprint-dev \
  -f evidence/phase-4.5/build-evidence/r-d2-plan-20260814/spec/PROMPT.md \
  -o json \
  > evidence/phase-4.5/build-evidence/r-d2-plan-20260814/spec/review-minimax-m3-envelope.json \
  2> evidence/phase-4.5/build-evidence/r-d2-plan-20260814/spec/review-minimax-m3-stderr.log
```

## After firing

Post VALIDATE COMPLETE rows per envelope and one REVIEW REQUEST row to
evidence/LEDGER.md. The referee audits and signs.

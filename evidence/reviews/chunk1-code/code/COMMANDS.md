# Exact commands (per operator logging directive)

## grok-4.5
```
droid exec --model grok-4.5 --output-format json --cwd /Users/factory/work/adversarial-sprint-dev "$(cat phase-4.5/build-evidence/r-chunk1-code-20260814-0020/code/PROMPT.md)"
```
PROMPT.md sha256: 867f54ba54ad0da4ddadb93ff705f78d90ca914f5de295e91a8be3837ea371ef
build commit: d5db8ff | judge sha256: 233eee9d0589d024e30dbe5c9fe02028ba358eeb732c0a83927c780748dec4a2

## Corrected invocation (attempt 2)
```
bash tools/run-with-model.sh droid exec --model grok-4.5 \
  -f phase-4.5/build-evidence/r-chunk1-code-20260814-0020/code/PROMPT.md \
  --auto low --enabled-tools Read,Grep,Glob,LS --output-format json --cwd "$PWD" \
  > <run>/grok-4.5.json 2> <run>/grok-4.5.stderr
```
Attempt 1 omitted `--auto low --enabled-tools` and burned; see BURNED.md.

## Attempt 3 — CORRECT: use the standard pipeline, not a hand-rolled call
```
python3 tools/orchestrate-review.py \
  --framework-root "$PWD" --pilot-root "$PWD" --pilot-python python3 \
  --test-file tests/test_layout_paths.py \
  --lock-file phase-1/locks/tests/test_layout_paths.py.lock.json \
  --prompt-file phase-4.5/build-evidence/r-chunk1-code-20260814-0020/code/PROMPT.md \
  --review-output-dir phase-4.5/build-evidence/r-chunk1-code-20260814-0020/code \
  --validators grok-4.5:xai:grok-family \
  --auto-level medium --enabled-tools Read,Glob,Grep,LS,Execute \
  --full-suite --allow-single-family
```
`--evidence-output` omitted deliberately: step 1 calls local_backend.py, which
cannot run on this machine's python3.9.6 (KI-1). Step 1 is skipped when the flag
is absent. `--allow-single-family` because the operator directed SEQUENTIAL
firing (grok first, gemini only if grok passes) to conserve frontier budget;
the second family follows in its own invocation.

Attempts 1 and 2 were hand-rolled `droid exec` calls and both failed on guards
this pipeline already encodes. See BURNED.md.

## Attempt 4 — gemini seat (second family), same prompt + same bytes
```
python3 tools/orchestrate-review.py \
  --framework-root "$PWD" --pilot-root "$PWD" --pilot-python python3 \
  --test-file tests/test_layout_paths.py \
  --lock-file phase-1/locks/tests/test_layout_paths.py.lock.json \
  --prompt-file <run>/PROMPT.md --review-output-dir <run> \
  --validators gemini-3.1-pro-preview:google:gemini-family \
  --auto-level medium --enabled-tools Read,Glob,Grep,LS,Execute \
  --full-suite --allow-single-family
```
Fired only after grok-4.5 returned ACCEPT-WITH-NITS, per operator direction to
sequence the seats and conserve frontier budget. Same PROMPT.md bytes
(sha256 867f54ba…), same repo state (da68fd0).

## Attempt 5 — gemini at low autonomy (attempt 4 burned: "Exec failed", turns=0 x3)
```
python3 tools/orchestrate-review.py ... \
  --validators gemini-3.1-pro-preview:google:gemini-family \
  --auto-level low --enabled-tools Read,Glob,Grep,LS \
  --full-suite --allow-single-family
```

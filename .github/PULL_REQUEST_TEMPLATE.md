## Chunk

<!-- PR title must include [chunk:<id>] so the CI runner can identify the chunk. -->

Chunk ID: `[chunk:]`

## Summary

<!-- What does this change do and why? -->

## Validation

- [ ] `python3 -m pytest -q` passes
- [ ] `python3 tools/wiki-link-audit.py` clean
- [ ] `python3 tools/plan-lint.py <spec>` PASS (if a spec file changed)
- [ ] Cross-family review fired (if code changed)

## Scope

<!-- List files or dirs touched. Confirm no out-of-scope edits. -->

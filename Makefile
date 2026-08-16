.PHONY: test lint format typecheck wiki-audit plan-lint review clean

## Run the full test suite
test:
	python3 -m pytest -q

## Lint all Python source (ruff)
lint:
	ruff check tools/ tests/

## Auto-fix lint issues where possible
lint-fix:
	ruff check --fix tools/ tests/

## Format all Python source (ruff format)
format:
	ruff format tools/ tests/

## Type-check all Python source (mypy)
typecheck:
	mypy tools/ tests/ --exclude 'tools/phase-1-hooks/' --exclude 'tools/fixtures/'

## Audit wiki links for dead anchors
wiki-audit:
	python3 tools/wiki-link-audit.py

## Lint a planning spec (usage: make plan-lint SPEC=path/to/spec.md)
plan-lint:
	@test -n "$(SPEC)" || (echo "Usage: make plan-lint SPEC=path/to/spec.md" && exit 1)
	python3 tools/plan-lint.py $(SPEC)

## Fire a cross-family review (usage: make review MODEL=prompt SPRINT=name)
review:
	@test -n "$(MODEL)" && test -n "$(SPRINT)" || (echo "Usage: make review MODEL=prompt-file SPRINT=sprint-name" && exit 1)
	bash tools/run-review.sh $(MODEL) $(SPRINT)

## Run all validation gates (test + lint + wiki-audit)
ci: test lint wiki-audit
	@echo "All gates passed."

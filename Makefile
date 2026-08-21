.PHONY: setup test test-cov lint format typecheck wiki-audit plan-lint review depcheck clean

## Fresh-clone setup: create venv, install deps, install pre-commit hooks
setup:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt
	.venv/bin/pip install pre-commit
	.venv/bin/pre-commit install
	@echo "Setup complete. Activate with: source .venv/bin/activate"

## Run the full test suite
test:
	python3 -m pytest -q

## Run tests with coverage gate (fails if coverage drops below 50%)
test-cov:
	python3 -m pytest --cov=tools --cov-report=term-missing --cov-fail-under=50

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

## Detect unused dependencies (deptry)
depcheck:
	deptry .

## Run all validation gates (test + lint + wiki-audit + coverage)
ci: test test-cov lint wiki-audit
	@echo "All gates passed."

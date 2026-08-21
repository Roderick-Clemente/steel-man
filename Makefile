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

## Run tests with coverage gate (floor, not a target — see note)
# 40, not 50. Measured coverage of tools/ is 44%, so a 50 gate fails the repo
# it ships in, and a gate set at exactly 44 is a tripwire that goes red the
# first time anyone adds an uncovered line. 40 is a floor that catches real
# regressions; raise it deliberately as coverage climbs.
#
# Read this number in context: tools/ contains ten historical phase-N-* dirs of
# one-off generators and fixtures kept as provenance, and they are counted here.
# The live runner's coverage is materially higher — measure tools/sprint_loop
# separately before quoting a figure.
test-cov:
	python3 -m pytest --cov=tools --cov-report=term-missing --cov-fail-under=40

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

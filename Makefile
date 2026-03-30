.PHONY: check fix typecheck test setup

check:
	uv run python -m ruff check src tests
	uv run python -m ruff format --check src tests
	$(MAKE) typecheck
	$(MAKE) test

fix:
	uv run python -m ruff check --fix src tests
	uv run python -m ruff format src tests

typecheck:
	uv run python -m pyright src

test:
	uv run python -m pytest tests -q

setup:
	uv sync
	uv run pre-commit install

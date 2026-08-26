.PHONY: install fmt lint clean

install:
	uv sync

fmt:
	uv run ruff format .

lint:
	uv run ruff check --fix .
	uv run ruff format --check .

clean:
	rm -rf .venv .pytest_cache .ruff_cache test-results playwright-report
	find . -type d -name __pycache__ -exec rm -rf {} +

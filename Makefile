.PHONY: install fmt lint test test-e2e test-all clean build up down logs

install:
	uv sync
	uv run playwright install chromium

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

fmt:
	uv run ruff format .

lint:
	uv run ruff check --fix .
	uv run ruff format --check .

test:
	uv run pytest

test-e2e:
	uv run pytest tests/e2e -v -m e2e --no-header -p no:cacheprovider --override-ini="addopts="

test-all: test test-e2e

clean:
	rm -rf .venv .pytest_cache .ruff_cache test-results playwright-report
	find . -type d -name __pycache__ -exec rm -rf {} +

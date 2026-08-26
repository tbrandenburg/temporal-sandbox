.PHONY: install fmt lint clean build up down logs

install:
	uv sync

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

clean:
	rm -rf .venv .pytest_cache .ruff_cache test-results playwright-report
	find . -type d -name __pycache__ -exec rm -rf {} +

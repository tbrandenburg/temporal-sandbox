.PHONY: install fmt lint test test-e2e test-all clean build up down logs record-history

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

record-history:
	@echo "Regenerating replay fixtures — requires the stack to be up (make up)."
	@temporal --address 127.0.0.1:7233 workflow start \
		--task-queue say_hello --type SayHelloWorkflow \
		--input '"Replay"' --workflow-id replay-say-hello
	@temporal --address 127.0.0.1:7233 workflow result -w replay-say-hello
	@temporal --address 127.0.0.1:7233 workflow show -w replay-say-hello -o json > tests/histories/say_hello.json
	@temporal --address 127.0.0.1:7233 workflow start \
		--task-queue sleep_greet --type SleepGreetWorkflow \
		--input '"Replay"' --workflow-id replay-sleep-greet
	@temporal --address 127.0.0.1:7233 workflow result -w replay-sleep-greet
	@temporal --address 127.0.0.1:7233 workflow show -w replay-sleep-greet -o json > tests/histories/sleep_greet.json
	@echo "Fixtures written to tests/histories/. Review the diff before committing."

clean:
	rm -rf .venv .pytest_cache .ruff_cache test-results playwright-report
	find . -type d -name __pycache__ -exec rm -rf {} +

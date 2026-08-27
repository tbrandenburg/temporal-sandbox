# AGENTS.md

Project-specific notes for agents working in this repository. See `docs/INITIAL.md` for the full
plan and architecture rationale, and `README.md` for full user-facing documentation.

## What this repo is

A local sandbox for developing and testing Temporal workflows, driven by the `temporal` CLI, the
Temporal Web UI, and a small Python starter script, all running against a Dockerized Temporal dev
server. The sandbox is generic: any workflow can be added as a self-contained "bundle" (activities
+ workflow + its own task queue) via the registry in `src/sandbox/registry.py`. It currently ships
two bundles: `say_hello` (quickstart) and `sleep_greet` (timer demo used to prove Durable Execution
survives a worker kill). No persistence, no Temporal Cloud, no Kubernetes — local dev only.

## Makefile targets

| Target | Purpose |
|---|---|
| `make install` | `uv sync` + install Playwright's chromium browser |
| `make build` | Build the worker Docker image |
| `make up` / `make down` | Start/stop the Temporal dev server + bundle workers in Docker |
| `make logs` | Follow Docker Compose logs |
| `make worker BUNDLE="name1 name2"` | Run the worker on the host, optionally scoped to specific bundles (unset = all) |
| `make run WF=<WorkflowClassName> ARG='<json>'` | Execute a workflow via the starter CLI and print its result |
| `make ui` | Print the Temporal Web UI URL |
| `make fmt` / `make lint` | ruff format / ruff check + format check |
| `make test` | Unit + integration + replay tests, no Docker required |
| `make test-e2e` | Full Docker stack + Playwright e2e suite (~30s) |
| `make test-all` | `test` + `test-e2e` |
| `make record-history` | Regenerate committed replay fixtures (requires `make up` first) |
| `make clean` | Remove caches, venv, and test artifacts |

## Lessons Learned

- 2026-08-26: The host `temporal` CLI fails with `context deadline exceeded` against
  `localhost:PORT` because `localhost` resolves to `::1` (IPv6) first while the dev server only
  binds IPv4. Always pass `--address 127.0.0.1:7233` explicitly (CLI invocations, Makefile
  targets, Docker healthchecks) — never bare `localhost`. Verify server connectivity issues
  against `127.0.0.1` before assuming the server itself is broken.
- 2026-08-26: A written implementation plan (`docs/INITIAL.md` §10) listed `make worker`/`make
  run`/`make ui` targets that later build steps never actually added, and this went unnoticed
  until the final documentation step cross-checked the plan against the real `Makefile`. When a
  plan enumerates specific interface surface (CLI flags, make targets, file paths), verify it was
  actually implemented — don't assume prior steps completed everything listed, especially for
  convenience wrappers that no test exercises directly.

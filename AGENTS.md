# AGENTS.md

Project-specific notes for agents working in this repository. See `docs/INITIAL.md` for the full
plan and architecture rationale, and `README.md` for full user-facing documentation.

## What this repo is

A local sandbox for developing and testing Temporal workflows, driven by the `temporal` CLI, the
Temporal Web UI, and a small Python starter script, all running against a Dockerized Temporal dev
server. The sandbox is generic: any workflow can be added as a self-contained "bundle" (activities
+ workflow + its own task queue) via the registry in `src/sandbox/registry.py`. It currently ships
ten bundles: `say_hello` (quickstart), `sleep_greet` (timer demo used to prove Durable Execution
survives a worker kill), `zigflow_greet` (a zigflow-DSL YAML workflow, executed by the external
`zigflow` binary, calling back into a Python activity — two processes instead of one),
`zigflow_agentic_workflow` (a ported zigflow.dev plan/act/observe agent-loop example, calling back
into Python activities that use opencode's free, keyless `big-pickle` model instead of the
upstream's Ollama), and five DSL-only zigflow example bundles adapted from zigflow.dev's docs
(`zigflow_hello_world`, `zigflow_http_call`, `zigflow_error_handling`, `zigflow_parallel_tasks`,
`zigflow_signal_driven`) — each has no Python activity at all. Every bundle folder also has an
executable `run.sh` for
ad-hoc local execution without Docker Compose (see `src/sandbox/workflows/_lib.sh`). No
persistence, no Temporal Cloud, no Kubernetes — local dev only.

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
| `make zigflow-validate` | Lint every `src/sandbox/workflows/*/workflow.yaml` via the `zigflow` CLI (wired into `lint`) |
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
- 2026-08-27: zigflow's `document.taskQueue` rejects underscores (must match
  `^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$`), so a zigflow-DSL bundle needs hyphenated
  wire-level task queue names (`zigflow-greet`, `zigflow-greet-activities`) even while its
  Python-side bundle name keeps the repo's underscore convention (`zigflow_greet`). Run `zigflow
  validate` (`make zigflow-validate`) against the YAML before wiring compose/starter changes, since
  it catches this and similar schema constraints early; note this also means such bundles have no
  `test_workflows.py`/`test_replay.py` coverage, since `WorkflowEnvironment`/`Replayer` require a
  Python workflow class that a DSL-only bundle doesn't have.
- 2026-08-27: The `ghcr.io/zigflow/zigflow` container reliably failed with `"failed reaching
  server: context deadline exceeded"` when dialing the Compose bridge-network hostname
  (`--temporal-address=temporal:7233`), even though the hostname resolved correctly and plain TCP
  connects from the same image succeeded — only the raw container IP or a shared network
  namespace worked. Root cause not fully isolated (likely a Go gRPC client DNS-resolution quirk in
  the zigflow binary), but the fix mirrors the existing `--address 127.0.0.1:7233` workaround for
  the host `temporal` CLI: give the zigflow service `network_mode: "service:temporal"` and address
  it via `127.0.0.1:7233` instead of the DNS hostname. When a new container image talks to
  `temporal` over the Compose network and only gets a deadline-exceeded error with no other
  symptom, suspect this class of hostname-resolution issue before debugging application logic —
  confirm with a raw-IP or shared-network-namespace probe before assuming the target service is
  unreachable or misconfigured.
- 2026-08-27: `zigflow run` binds fixed default ports for its Prometheus metrics server
  (`0.0.0.0:9090`) and health-check server (`0.0.0.0:3000`). On a host where anything else already
  holds either port, `zigflow run` exits with a fatal bind error and silently never registers the
  workflow — a subsequent `temporal workflow start`/`execute_workflow` then hangs waiting for a
  worker that doesn't exist, with no obvious error pointing back at the port collision (only
  visible by reading the backgrounded process's own stderr). Any script that starts `zigflow run`
  in the background (e.g. per-bundle `run.sh`) must pass
  `--metrics-listen-address 127.0.0.1:0 --health-listen-address 127.0.0.1:0` (or otherwise pick
  free ports) rather than relying on the defaults, and should be smoke-tested end-to-end against a
  real Temporal server at least once — `bash -n` syntax checks alone cannot catch this class of
  runtime port-collision failure.
- 2026-08-27: For a zigflow DSL workflow whose top-level `do:` block is a multi-task state machine
  (several named tasks wired together via `switch.then` jumps, e.g. the ported
  `zigflow_agentic_workflow` bundle), zigflow registers each top-level `do:` key as its own callable
  Temporal workflow type — the identifier actually invocable via `client.execute_workflow` is the
  first top-level key's name, not the `document.workflowType` metadata field. All of this repo's
  other multi-task zigflow bundles already follow this (`try-catch`, `competing-tasks`, `signal`,
  `fetch-user` as `workflowType`, matching their first `do:` key) but it went unnoticed until a new
  bundle was ported with a PascalCase `workflowType` that didn't match any registered type, causing
  `test_dsl_task_queue_matches_registry` to fail only once the bundle was actually exercised
  end-to-end. Always set `document.workflowType` to the exact name of the first top-level `do:` key
  for multi-task DSL workflows, and verify with a real `run.sh` execution (not just
  `zigflow validate`, which does not catch this class of mismatch) before trusting the wiring.
- 2026-08-27: The `INPUT="${1:-{\"key\":\"value\"}}"` bash default-argument pattern (used in
  `zigflow_greet/run.sh` and copied into new `run.sh` scripts) silently corrupts JSON when an
  explicit `$1` is supplied, because bash's brace-matching in parameter expansion still appends a
  spurious trailing `}` to the substituted value. It stayed unnoticed because no bundle's `run.sh`
  had ever been invoked with an explicit override argument. Always assign the default JSON to a
  separate variable first (`DEFAULT_INPUT='{...}'; INPUT="${1:-$DEFAULT_INPUT}"`) and test `run.sh`
  with an explicit argument at least once, not just with its default.

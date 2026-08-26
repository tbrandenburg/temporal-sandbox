# temporal-sandbox — Initial Plan

A local sandbox for developing and testing **arbitrary Temporal workflows**, driven by the
Temporal CLI and Web UI, running in Docker, verified end-to-end with Playwright.

Status: **planned, not yet implemented**.

---

## 1. Goal

One repository in which any number of Temporal workflows can be dropped in, run in isolation,
inspected via the CLI and the Web UI, and covered by tests. The Quickstart `SayHello` workflow
is the first inhabitant, not the purpose.

Non-goal: a production deployment. Everything below is scoped to a local developer sandbox.

---

## 2. Environment (verified)

| Item | Value |
|---|---|
| Temporal CLI | `1.8.2` (Server `1.31.2`, UI `2.50.1`) at `/home/linuxbrew/.linuxbrew/opt/temporal/bin/` |
| Python | `3.12.3` |
| Package manager | `uv` |
| Repo state | empty git repo |

---

## 3. Research summary

Sources read in full:
[set-up-your-local-python](https://docs.temporal.io/develop/python/set-up-your-local-python),
[cli](https://docs.temporal.io/cli),
[web-ui](https://docs.temporal.io/web-ui),
[testing-suite](https://docs.temporal.io/develop/python/testing-suite),
[best-practices](https://docs.temporal.io/best-practices/) (+ `error-handling`, `worker`,
`pre-production-testing`, Python `error-handling`),
[self-hosted-guide/deployment](https://docs.temporal.io/self-hosted-guide/deployment).

### 3.1 Applicable findings

- **Dev server**: `temporal server start-dev` → gRPC `localhost:7233`, Web UI `localhost:8233`,
  in-memory DB, auto-creates the `default` namespace. Docs explicitly recommend it for local
  development and testing; the Postgres/Elasticsearch Compose stack is for
  *"sustained workloads that exceed what the development server is designed to handle"*.
- **Task queues**: *"Use separate Task Queues for distinct workloads."* A task-queue name mismatch
  between client and worker is **silent** — it creates a second queue and the worker never receives
  tasks. Define the name once as a constant referenced by both.
- **Worker config**: inject all connection parameters at runtime via environment variables or CLI
  flags; workers are CI/CD artifacts.
- **Graceful shutdown**: abrupt worker shutdown triggers expensive retries and timeouts for
  in-flight activities. Use a graceful shutdown timeout.
- **Testing**: *"We generally recommend writing the majority of your tests as integration tests."*
  `WorkflowEnvironment.start_time_skipping()` for fast timers, `start_local()` for a real local
  server, `ActivityEnvironment` for activities in isolation.
- **Replay testing**: recommended as an explicit **CI check** — download event histories, run them
  through `Replayer`, fail CI on error. Caveat: exported histories may be protobuf-encoded, causing
  `dict` vs `bytes` `TypeError` if not decoded.
- **Pre-production testing**: the first and cheapest scenario is *"kill all Workers, then restart
  them"*, validating at-least-once semantics and clean replay.
- **Security**: never expose Temporal hosts to the open internet.

### 3.2 Deliberately excluded

Temporal Cloud (access control, APS limits, cost optimization/governance, multi-tenancy, region
failover), Helm/Kubernetes, Temporal Server binaries or Go-import deployment, Postgres,
Elasticsearch, Worker Versioning and patching, poller/slot/sticky-cache tuning, metrics dashboards
and alerting, Continue-As-New and event-history growth, Claim Check, Saga, mTLS/API keys,
ToxiProxy/Chaos Mesh, registry publishing, mypy, Node/TypeScript toolchain.

These are production and Cloud concerns. Adding them to a local sandbox is overengineering.

---

## 4. Decisions

| # | Decision | Rationale |
|---|---|---|
| 1 | Single Docker Compose stack running `temporal server start-dev` | Docs recommend the dev server for local work |
| 2 | No Postgres, no Elasticsearch, no persistence | Nothing in scope requires durable storage |
| 3 | `full` Postgres profile **dropped** | With no persistence and no ES requirement it is dead weight no test exercises |
| 4 | Ports `7233` / `8233`, published on `127.0.0.1` only | UI port standardized across host and Docker; loopback bind per security guidance |
| 5 | Tests run on the **host**, targeting the **Docker** stack | Reproducible stack without complicating Playwright |
| 6 | Worker image built **locally**, no registry push | Sandbox scope |
| 7 | One task queue **per bundle**, not one shared queue | Isolation between unrelated workflows; docs' "separate Task Queues logically" |
| 8 | Test weighting ≈ **20 unit / 50 integration / 30 e2e+replay** | Temporal docs recommend integration-heavy; unit-testing workflow methods in isolation has little signal |

Decision 8 deviates from the generic 50/30/20 pyramid, intentionally and on the record.

---

## 5. Architecture

### 5.1 Registry

The sandbox is generic: one worker entrypoint and one starter entrypoint, driven by a registry.
Adding a workflow = drop a package under `src/sandbox/workflows/` and call `register()`.

```python
# src/sandbox/registry.py
@dataclass(frozen=True)
class Bundle:
    name: str
    workflows: list[type]
    activities: list[Callable]
    task_queue: str = ""   # defaults to name

REGISTRY: dict[str, Bundle] = {}
def register(bundle: Bundle) -> None: ...
def resolve(names: list[str] | None) -> list[Bundle]: ...
```

### 5.2 Workflow selection — identical semantics on all three surfaces

```bash
SANDBOX_BUNDLES=say_hello,sleep_greet          # docker env
python -m sandbox.worker --bundle say_hello    # repeatable flag
make worker BUNDLE="say_hello sleep_greet"
```

- Unset ⇒ all registered bundles.
- Unknown name ⇒ **fail fast**, listing the valid names.
  Never a silent no-op: a bundle or task-queue typo otherwise manifests as a worker that polls
  forever and receives nothing.

### 5.3 Worker

One `Worker` per selected bundle, run concurrently via `asyncio.gather`, each on its own task
queue. Graceful shutdown on `SIGINT`/`SIGTERM` with `graceful_shutdown_timeout`.

### 5.4 Configuration

`src/sandbox/config.py`, all env-overridable, imported by both worker and starter so the task
queue constant can never drift:

`TEMPORAL_ADDRESS` (default `localhost:7233`), `TEMPORAL_NAMESPACE` (`default`),
`TEMPORAL_UI_URL` (`http://localhost:8233`), `SANDBOX_BUNDLES`.

---

## 6. Repository layout

```
Makefile
pyproject.toml                 # deps + ruff + pytest config, single file
docker-compose.yml
Dockerfile                     # worker image, multi-stage uv, non-root
.dockerignore
.gitignore
README.md
docs/INITIAL.md                # this document
src/sandbox/
  __init__.py
  config.py
  registry.py
  worker.py                    # python -m sandbox.worker [--bundle NAME]...
  starter.py                   # python -m sandbox.starter <Workflow> <json-arg>
  workflows/
    __init__.py                # imports subpackages -> triggers register()
    say_hello/
      activities.py            # greet()
      workflow.py              # SayHelloWorkflow + register(Bundle(...))
    sleep_greet/
      activities.py
      workflow.py              # contains a timer -> enables the worker-kill test
tests/
  conftest.py
  test_activities.py           # ActivityEnvironment
  test_workflows.py            # start_time_skipping + Worker + mocked activity
  test_replay.py               # determinism guard
  histories/*.json             # committed replay fixtures
  e2e/
    conftest.py                # compose up/down + readiness poll
    test_workflow_e2e.py
    test_cli_e2e.py
    test_ui_e2e.py
    test_worker_restart.py
```

---

## 7. Docker

### 7.1 Server service

```
temporal server start-dev --ip 0.0.0.0 --ui-ip 0.0.0.0 --ui-port 8233
```

Published as `127.0.0.1:7233:7233` and `127.0.0.1:8233:8233`, with a healthcheck.
Binding `0.0.0.0` *inside* the container is required for reachability; the host-side publish
restricts exposure to loopback.

The host CLI at `/home/linuxbrew/.linuxbrew/opt/temporal/bin/temporal` works unchanged against
`localhost:7233`.

> **Unverified**: the exact image for a containerized dev server (`temporalio/temporal` vs
> `temporalio/admin-tools`). To be confirmed by pulling and running it in build step 1, not assumed.

### 7.2 Worker services

One service per bundle (`worker-say_hello`, `worker-sleep_greet`), all using the same locally built
image and differing only by `SANDBOX_BUNDLES`. This makes `docker compose up worker-say_hello` run
exactly one bundle, and lets the restart test kill one worker without disturbing the other.

Image: multi-stage `uv` build, slim base, non-root user, entrypoint `python -m sandbox.worker`,
all configuration from environment variables.

---

## 8. Tooling

- **uv** — environment and dependencies
- **ruff** — format *and* lint (replaces black/isort/flake8)
- **pytest** + `pytest-asyncio` (`asyncio_mode = "auto"`)
- **pytest-playwright** — Playwright in Python, so no Node toolchain enters the repo
- No mypy initially; the typed SDK plus ruff rules cover most of the value

---

## 9. Test strategy

| Layer | Scope | Mocks |
|---|---|---|
| Unit | `ActivityEnvironment().run(greet, "X")` | n/a |
| Integration | `WorkflowEnvironment.start_time_skipping()` + `Worker` with a mocked activity | activity only |
| Replay | `Replayer` over committed event histories | none |
| E2E | Real Docker stack + real workers | **none** |

### 9.1 E2E coverage

1. **Workflow** — starter executes it, result asserted (`Hello Temporal`).
2. **CLI** — `temporal workflow start --task-queue say_hello --type SayHelloWorkflow --input '"Temporal"' --workflow-id <id>`,
   then `temporal workflow result -w <id>` and `temporal workflow describe -w <id> -o json`,
   asserting `WORKFLOW_EXECUTION_COMPLETED`.
3. **UI** — Playwright opens `http://localhost:8233/namespaces/default/workflows/<id>`, asserts the
   status badge reads *Completed*, the workflow type is correct, and the History tab renders
   `ActivityTaskCompleted`. Screenshot to `.playwright/` on failure.
4. **Worker restart** — start `sleep_greet`, `SIGKILL` its worker mid-timer, restart it, assert the
   workflow still completes. This is the only test that actually proves Durable Execution rather
   than asserting a string.

### 9.2 Replay fixtures

`make record-history WF=<id>` writes `temporal workflow show -w <id> -o json` into
`tests/histories/`. Fixtures are committed; `test_replay.py` runs in `make test` and fails on any
non-determinism. Decode protobuf-encoded histories before passing them to the `Replayer`.

---

## 10. Makefile

```
make install                  # uv sync + playwright install chromium
make build                    # build the worker image
make up / make down           # compose stack, detached
make logs                     # follow
make worker [BUNDLE="..."]    # host-side worker
make run WF=... ARG=...       # start a workflow
make ui                       # open http://localhost:8233
make fmt                      # ruff format
make lint                     # ruff check --fix + format --check
make test                     # unit + integration + replay (no docker)
make test-e2e                 # up -> e2e (workflow, CLI, UI, restart) -> down
make test-all                 # test + test-e2e
make record-history WF=<id>   # refresh replay fixtures
make clean                    # caches and artifacts
```

---

## 11. Build order

Each step is verified with real command output before the next begins.

1. Confirm the dev-server image runs: `make up`, then
   `temporal operator namespace describe default` succeeds and the UI returns HTTP 200 on `8233`
2. `pyproject.toml`, `Makefile`, `.gitignore` → `make install` green
3. `config.py`, `registry.py`, `say_hello`, `worker.py`, `starter.py` → manual smoke test
4. `Dockerfile` + compose worker services → `make build && make up && make run`
5. `make lint` green
6. Unit + integration tests → `make test` green
7. `sleep_greet` bundle
8. E2E: workflow → CLI → Playwright UI → worker restart
9. Replay fixtures + `test_replay.py`, folded into `make test`
10. `README.md`

---

## 12. Deferred, cheap to add later

- **Error-handling demo bundle**: `ApplicationError(type=..., non_retryable=True)`, explicit
  `RetryPolicy`, idempotency key from `f"{info.workflow_run_id}-{info.activity_id}"`.
  Workflow-local code — the registry needs no change.
- **Persistence**: a `docker-compose.full.yml` override adding Postgres and a named volume,
  roughly 20 lines.
- **CI**: GitHub Actions running `make lint test test-e2e`; the dev server runs fine in CI.

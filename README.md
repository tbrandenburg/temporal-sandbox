# temporal-sandbox

A local sandbox for developing and testing Temporal workflows, driven by the `temporal` CLI, the
Temporal Web UI, and a small Python starter script, all running against a Dockerized Temporal dev
server. The sandbox itself is generic: any workflow can be added as a self-contained "bundle"
(activities + workflow + its own task queue). It currently ships two bundles: `say_hello` (a
minimal quickstart) and `sleep_greet` (a timer-based demo used to exercise Durable Execution via a
worker-restart test).

## Prerequisites

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/)
- Docker and Docker Compose
- The `temporal` CLI on `PATH` (or otherwise resolvable) — used to drive workflows and to record
  replay fixtures. Verified against CLI `1.8.2` / Server `1.31.2` / UI `2.50.1`.

## Quickstart

```bash
make install                              # uv sync + install Playwright's chromium browser
make up                                   # start the Temporal dev server + all bundle workers in Docker
make run WF=SayHelloWorkflow ARG='"Temporal"'
```

`make run` wraps `starter.py`: it takes a workflow class name (`WF`) and a single JSON-encoded
argument (`ARG`), resolves the task queue from the bundle registry, executes the workflow, and
prints the result:

```bash
make run WF=SayHelloWorkflow ARG='"Temporal"'
# Hello Temporal

make run WF=SleepGreetWorkflow ARG='"Temporal"'
# Hello (after a nap) Temporal
```

You can also run the starter directly if you prefer: `uv run python -m sandbox.starter <WF> <ARG>`.

Tear down with `make down`.

## Architecture

### Bundle registry

One worker entrypoint (`src/sandbox/worker.py`) and one starter entrypoint
(`src/sandbox/starter.py`) are driven by a small registry (`src/sandbox/registry.py`):

```python
@dataclass(frozen=True)
class Bundle:
    name: str
    workflows: list[type]
    activities: list[Callable]
    task_queue: str = ""  # defaults to `name`


REGISTRY: dict[str, Bundle] = {}


def register(bundle: Bundle) -> None: ...
def resolve(names: list[str] | None) -> list[Bundle]: ...
```

Each bundle gets its own task queue (defaulting to the bundle name), so workflows from different
bundles never collide, and a worker can be scoped to serve only a subset of bundles.

### Adding a new workflow

1. Create `src/sandbox/workflows/<name>/` with an `__init__.py`.
2. Define `activities.py` (plain `@activity.defn` functions).
3. Define `workflow.py` with a `@workflow.defn` class, then call
   `register(Bundle(name="<name>", workflows=[...], activities=[...]))` at module scope.
4. Add `from sandbox.workflows.<name> import workflow as _<name>_workflow` to
   `src/sandbox/workflows/__init__.py` so importing that package triggers the `register()` side
   effect.
5. Optionally add a `worker-<name>` service to `docker-compose.yml` (copy an existing one, set
   `SANDBOX_BUNDLES: <name>`) so the bundle runs as its own container.

No changes to `worker.py`, `starter.py`, or `registry.py` are needed.

## Running workflows

Three equivalent surfaces, all pointed at the same dev server:

**Starter CLI**

```bash
make run WF=SayHelloWorkflow ARG='"Temporal"'
```

**`temporal` CLI**

```bash
temporal --address 127.0.0.1:7233 workflow start \
  --task-queue say_hello --type SayHelloWorkflow \
  --input '"Temporal"' --workflow-id my-id

temporal --address 127.0.0.1:7233 workflow result -w my-id
temporal --address 127.0.0.1:7233 workflow describe -w my-id -o json
```

**Web UI**

Open `http://127.0.0.1:8233` (or run `make ui` to print the URL) and navigate to
`namespaces/default/workflows/<workflow-id>`.

> **Important**: always pass `--address 127.0.0.1:7233`, never `localhost:7233`. On some hosts
> `localhost` resolves to `::1` (IPv6) first, but the dev server only binds IPv4, producing a
> connection failure that looks like the server isn't running when it actually is.

## Selecting bundles

All three mechanisms share the same semantics (unset = all registered bundles; unknown name = fail
fast, listing valid bundle names — never a silent no-op):

```bash
SANDBOX_BUNDLES=say_hello,sleep_greet          # env var, comma-separated (used in docker-compose.yml)
make worker BUNDLE="say_hello sleep_greet"     # repeatable --bundle flag, space-separated in BUNDLE
uv run python -m sandbox.worker --bundle say_hello --bundle sleep_greet   # equivalent, direct
uv run python -m sandbox.worker                                          # no args -> all bundles
```

## Testing

```bash
make test        # unit + integration + replay, no Docker required
make test-e2e     # full Docker stack + Playwright, ~30s
make test-all     # test + test-e2e
```

Per `docs/INITIAL.md` §9, the layers are:

| Layer | Scope | Mocks |
|---|---|---|
| Unit (`test_activities.py`) | `ActivityEnvironment().run(greet, ...)` per bundle | n/a |
| Integration (`test_workflows.py`) | `WorkflowEnvironment.start_time_skipping()` + `Worker` | none needed (real activities) |
| Replay (`test_replay.py`) | `Replayer` over committed histories in `tests/histories/` | none |
| E2E (`tests/e2e/`) | Real Docker stack: starter, `temporal` CLI, Web UI (Playwright), worker restart | none |

`make record-history` (requires `make up` first) regenerates the committed replay fixtures for
both bundles by starting fresh `SayHelloWorkflow`/`SleepGreetWorkflow` executions under fixed
workflow IDs and re-exporting their history via `temporal workflow show -o json`; review the diff
before committing.

## Development

```bash
make fmt    # ruff format
make lint   # ruff check --fix + ruff format --check
```

## Project layout

```
Makefile                        # install/build/up/down/logs/worker/run/ui/fmt/lint/test/test-e2e/test-all/record-history/clean
pyproject.toml                  # deps, ruff config, pytest config (single file)
docker-compose.yml              # temporal dev-server service + one worker service per bundle
Dockerfile                      # multi-stage uv build, non-root worker image
docs/INITIAL.md                 # the original plan/decisions document
src/sandbox/
  config.py                     # env-overridable TEMPORAL_ADDRESS / NAMESPACE / UI_URL / SANDBOX_BUNDLES
  registry.py                   # Bundle dataclass + register()/resolve()
  worker.py                     # python -m sandbox.worker [--bundle NAME]...
  starter.py                    # python -m sandbox.starter <WorkflowName> <json-arg>
  workflows/
    __init__.py                 # imports each bundle subpackage -> triggers register()
    say_hello/
      activities.py             # greet()
      workflow.py                # SayHelloWorkflow + register(Bundle(...))
    sleep_greet/
      activities.py             # greet() (post-sleep greeting)
      workflow.py                # SleepGreetWorkflow (10s timer) + register(Bundle(...))
tests/
  test_activities.py            # ActivityEnvironment unit tests
  test_workflows.py             # start_time_skipping + Worker integration tests
  test_replay.py                # replay determinism guard over tests/histories/*.json
  histories/                    # committed replay fixtures (say_hello.json, sleep_greet.json)
  e2e/
    conftest.py                 # compose up/down + readiness poll fixture
    test_workflow_e2e.py        # starter CLI against the real stack
    test_cli_e2e.py             # temporal CLI start/result/describe
    test_ui_e2e.py              # Playwright assertions against the Web UI
    test_worker_restart.py      # SIGKILL a worker mid-timer, assert the workflow still completes
```

## Scope / non-goals

This is a local developer sandbox, not a production deployment (`docs/INITIAL.md` §3.2 and §1).
Explicitly out of scope: Temporal Cloud, Kubernetes/Helm, persistence (no Postgres, no
Elasticsearch), worker versioning, metrics/alerting, mTLS/API keys, and CI. The dev server runs
fully in-memory; nothing here is meant to survive a restart of the `temporal` container itself.

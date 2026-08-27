# temporal-sandbox

A local sandbox for developing and testing Temporal workflows, driven by the `temporal` CLI, the
Temporal Web UI, and a small Python starter script, all running against a Dockerized Temporal dev
server. The sandbox itself is generic: any workflow can be added as a self-contained "bundle"
(activities + workflow + its own task queue). It currently ships three bundles: `say_hello` (a
minimal quickstart), `sleep_greet` (a timer-based demo used to exercise Durable Execution via a
worker-restart test), and `zigflow_greet` (a demo of a zigflow-DSL-defined workflow — YAML, executed
by the separate `zigflow` CLI/binary — calling back into a Python-implemented activity; unlike the
other two, it runs as two separate processes/services instead of one).

It also ships five DSL-only zigflow example bundles, adapted from
[zigflow.dev's examples](https://zigflow.dev/docs/examples/) and each demonstrating a single DSL
feature with no Python activities at all:

- `zigflow_hello_world` — minimal `set`/`output.as` example, no external calls (workflow type
  `hello-world`, task queue `zigflow-hello-world`)
- `zigflow_http_call` — `call: http` example fetching a user profile from a public JSON API
  (workflow type `fetch-user`, task queue `zigflow-http-call`)
- `zigflow_error_handling` — `try`/`catch` example recovering from a failing HTTP call (workflow
  type `try-catch`, task queue `zigflow-error-handling`)
- `zigflow_parallel_tasks` — `fork`/`compete: true` example racing two HTTP calls, first one wins
  (workflow type `competing-tasks`, task queue `zigflow-parallel-tasks`)
- `zigflow_signal_driven` — `listen` example that pauses for an external Temporal signal named
  `approve` before completing (workflow type `signal`, task queue `zigflow-signal-driven`)

## Prerequisites

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/)
- Docker and Docker Compose (`make up`/`make build` also pull `ghcr.io/zigflow/zigflow:0.15.0-rc1`,
  the DSL engine that runs the `zigflow_greet` bundle's workflow)
- The `temporal` CLI on `PATH` (or otherwise resolvable) — used to drive workflows and to record
  replay fixtures. Verified against CLI `1.8.2` / Server `1.31.2` / UI `2.50.1`.
- The `zigflow` CLI on `PATH` (`brew install --cask zigflow` via `brew tap zigflow/tap`) — only
  needed for `make lint`/`make zigflow-validate` and `tests/test_zigflow_definition.py`; not
  required to run the Docker stack itself.

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

make run WF=ZigflowGreetWorkflow ARG='{"name":"Ziggy"}'
# HELLO ZIGGY
```

`zigflow_greet`'s workflow logic lives in `workflow.yaml`, executed by the `zigflow` CLI/binary, not
in a Python `@workflow.defn` class — only its activity is Python. Run `make zigflow-validate` to
lint that YAML definition (schema + task-queue naming rules) without starting the Docker stack.

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
    workflows: list[type] = field(default_factory=list)
    activities: list[Callable] = field(default_factory=list)
    dsl_workflows: dict[str, str] = field(default_factory=dict)  # DSL workflow type -> queue
    task_queue: str = ""  # defaults to `name`


REGISTRY: dict[str, Bundle] = {}


def register(bundle: Bundle) -> None: ...
def resolve(names: list[str] | None) -> list[Bundle]: ...
```

Each bundle gets its own task queue (defaulting to the bundle name), so workflows from different
bundles never collide, and a worker can be scoped to serve only a subset of bundles. A bundle needs
either `workflows` or `activities` populated; `zigflow_greet` has only `activities` plus
`dsl_workflows`, since its workflow is a zigflow-DSL YAML file, not a Python `@workflow.defn` class.

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

If the workflow logic is a zigflow YAML DSL definition instead of a Python `@workflow.defn` class
(see `zigflow_greet` for a worked example), skip steps 2–3's workflow class and instead: register a
`Bundle` with only `activities` populated plus `dsl_workflows={"<WorkflowType>": "<task-queue>"}`,
add a second `zigflow-<name>` Compose service running `ghcr.io/zigflow/zigflow` against the YAML
file, and run `zigflow validate <file>` before wiring anything else — it catches schema issues
(e.g. `document.taskQueue` rejecting underscores) far faster than a failed Docker run. Note that
Compose service needs `network_mode: "service:temporal"` and `--temporal-address=127.0.0.1:7233`,
not the bridge-network hostname — see the 2026-08-27 Lessons Learned entries in `AGENTS.md` for why.

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

### Running a single bundle locally (ad-hoc, no Docker Compose)

Every bundle folder under `src/sandbox/workflows/<bundle>/` has an executable `run.sh`:

```bash
./src/sandbox/workflows/say_hello/run.sh                # uses a default input
./src/sandbox/workflows/say_hello/run.sh '"Ziggy"'       # optional JSON input arg
./src/sandbox/workflows/zigflow_hello_world/run.sh
```

Each script: checks whether a Temporal dev server is already reachable at `127.0.0.1:7233` and, if
not, starts one and tears it down afterwards (an already-running server is never touched); starts
whichever worker or `zigflow` process that bundle needs; triggers the workflow and prints the
result; and cleans up whatever processes it started, in `trap ... EXIT`.

These scripts are a local convenience layer, sourcing shared helpers from
`src/sandbox/workflows/_lib.sh`. They are **not** wired into `make lint`/`make fmt`/`make
test`/CI — they're a separate surface from `make run`/`make worker`/`make up`, useful for quickly
poking at one bundle without touching Docker Compose. Use whichever surface fits: Docker-based or
CI-driven work still goes through the Makefile targets.

`zigflow_signal_driven/run.sh` is the one exception to the "just calls `sandbox.starter`" pattern:
since that workflow blocks on `listen` waiting for an external signal, its script also issues a
`temporal workflow signal --name approve` call partway through before fetching the result.

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

`zigflow_greet` has no `test_workflows.py`/`test_replay.py` coverage: both `WorkflowEnvironment` and
`Replayer` require a Python workflow class, which this bundle doesn't have — its workflow logic is
YAML executed by the external `zigflow` binary. Instead it's covered by `test_zigflow_definition.py`
(YAML/Python drift + `zigflow validate`, see `make zigflow-validate`) and by
`tests/e2e/test_zigflow_ui_e2e.py`, which is the only test that exercises the full DSL-worker +
Python-worker chain end to end.

The same applies to the five DSL-only example bundles (`zigflow_hello_world`, `zigflow_http_call`,
`zigflow_error_handling`, `zigflow_parallel_tasks`, `zigflow_signal_driven`): they're parametrized
alongside `zigflow_greet` in `test_zigflow_definition.py` (schema/task-queue drift + `zigflow
validate`), but only `zigflow_greet` has UI e2e coverage — the five example bundles have no
`tests/e2e/` coverage at all.

`make record-history` (requires `make up` first) regenerates the committed replay fixtures for
both bundles by starting fresh `SayHelloWorkflow`/`SleepGreetWorkflow` executions under fixed
workflow IDs and re-exporting their history via `temporal workflow show -o json`; review the diff
before committing.

## Development

```bash
make fmt    # ruff format
make lint   # ruff check --fix + ruff format --check + zigflow validate (zigflow_greet's workflow.yaml)
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
    _lib.sh                      # shared helpers sourced by each bundle's run.sh
    say_hello/
      activities.py             # greet()
      workflow.py                # SayHelloWorkflow + register(Bundle(...))
      run.sh                     # ad-hoc local run, no Docker Compose
    sleep_greet/
      activities.py             # greet() (post-sleep greeting)
      workflow.py                # SleepGreetWorkflow (10s timer) + register(Bundle(...))
      run.sh                     # ad-hoc local run, no Docker Compose
    zigflow_greet/
      activities.py             # shout_greet() (only Python part of this bundle)
      __init__.py                # register(Bundle(dsl_workflows={"ZigflowGreetWorkflow": "zigflow-greet"}, ...))
      workflow.yaml               # zigflow DSL definition; no Python workflow.py
      run.sh                     # ad-hoc local run, no Docker Compose
    zigflow_hello_world/
      __init__.py                # register(Bundle(dsl_workflows=..., no activities))
      workflow.yaml               # minimal set/output.as example
      run.sh                     # ad-hoc local run, no Docker Compose
    zigflow_http_call/
      __init__.py                # register(Bundle(dsl_workflows=..., no activities))
      workflow.yaml               # call: http example
      run.sh                     # ad-hoc local run, no Docker Compose
    zigflow_error_handling/
      __init__.py                # register(Bundle(dsl_workflows=..., no activities))
      workflow.yaml               # try/catch example
      run.sh                     # ad-hoc local run, no Docker Compose
    zigflow_parallel_tasks/
      __init__.py                # register(Bundle(dsl_workflows=..., no activities))
      workflow.yaml               # fork/compete: true example
      run.sh                     # ad-hoc local run, no Docker Compose
    zigflow_signal_driven/
      __init__.py                # register(Bundle(dsl_workflows=..., no activities))
      workflow.yaml               # listen (external signal) example
      run.sh                     # ad-hoc local run; also sends the 'approve' signal mid-execution
tests/
  test_activities.py            # ActivityEnvironment unit tests
  test_workflows.py             # start_time_skipping + Worker integration tests (say_hello, sleep_greet only)
  test_replay.py                # replay determinism guard over tests/histories/*.json (say_hello, sleep_greet only)
  test_zigflow_definition.py     # YAML/Python drift guards + `zigflow validate` for zigflow_greet
  histories/                    # committed replay fixtures (say_hello.json, sleep_greet.json)
  e2e/
    conftest.py                 # compose up/down + readiness poll fixture
    test_workflow_e2e.py        # starter CLI against the real stack
    test_cli_e2e.py             # temporal CLI start/result/describe
    test_ui_e2e.py              # Playwright assertions against the Web UI
    test_worker_restart.py      # SIGKILL a worker mid-timer, assert the workflow still completes
    test_zigflow_ui_e2e.py      # zigflow_greet: DSL worker + Python worker cross-process chain via the Web UI
```

## Scope / non-goals

This is a local developer sandbox, not a production deployment (`docs/INITIAL.md` §3.2 and §1).
Explicitly out of scope: Temporal Cloud, Kubernetes/Helm, persistence (no Postgres, no
Elasticsearch), worker versioning, metrics/alerting, mTLS/API keys, and CI. The dev server runs
fully in-memory; nothing here is meant to survive a restart of the `temporal` container itself.

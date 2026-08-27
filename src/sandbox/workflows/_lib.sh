#!/usr/bin/env bash
# _lib.sh — shared helper functions for per-bundle run.sh scripts.
#
# This file is meant to be SOURCED by each bundle's run.sh (e.g.
# `source "$(dirname "${BASH_SOURCE[0]}")/../_lib.sh"`), never executed
# directly. It is not wired into make lint/fmt/test on purpose.
#
# Callers may be invoked from any directory; every function here resolves
# the repo root itself (via git) and uses subshells with explicit `cd` so
# the caller's CWD is never permanently changed. This matters for zigflow,
# whose `workflow.yaml` is resolved relative to the bundle's own directory.

set -euo pipefail

SANDBOX_REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "ERROR: _lib.sh must be sourced from within the temporal-sandbox git repo" >&2
  exit 1
}

TEMPORAL_ADDRESS="127.0.0.1:7233"

SANDBOX_WE_STARTED_TEMPORAL=0
SANDBOX_STARTED_TEMPORAL_PID=""
SANDBOX_WORKER_PIDS=()

# sandbox_ensure_temporal — start a local dev Temporal server if one isn't
# already reachable on 127.0.0.1:7233. Never touches a pre-existing server.
sandbox_ensure_temporal() {
  if temporal --address "$TEMPORAL_ADDRESS" operator namespace describe default >/dev/null 2>&1; then
    echo "Temporal already reachable at ${TEMPORAL_ADDRESS}, reusing it."
    SANDBOX_WE_STARTED_TEMPORAL=0
    return 0
  fi

  echo "Temporal not reachable at ${TEMPORAL_ADDRESS}, starting a local dev server..."
  temporal server start-dev --ip 0.0.0.0 --ui-ip 0.0.0.0 &
  SANDBOX_STARTED_TEMPORAL_PID=$!
  SANDBOX_WE_STARTED_TEMPORAL=1

  local waited=0
  local timeout=20
  while ! temporal --address "$TEMPORAL_ADDRESS" operator namespace describe default >/dev/null 2>&1; do
    sleep 1
    waited=$((waited + 1))
    if [ "$waited" -ge "$timeout" ]; then
      echo "ERROR: Temporal dev server did not become reachable within ${timeout}s" >&2
      return 1
    fi
  done
  echo "Temporal dev server is up (pid ${SANDBOX_STARTED_TEMPORAL_PID})."
}

# sandbox_start_worker <bundle_name> — start the sandbox worker for a bundle
# in the background, from the repo root.
sandbox_start_worker() {
  local bundle_name="$1"
  echo "Starting worker for bundle '${bundle_name}'..."
  (cd "$SANDBOX_REPO_ROOT" && exec uv run python -m sandbox.worker --bundle "$bundle_name") &
  SANDBOX_WORKER_PIDS+=("$!")
  sleep 2
}

# sandbox_start_zigflow <workflow_yaml_path> — start the zigflow runner for a
# DSL workflow in the background, from the directory containing the yaml.
sandbox_start_zigflow() {
  local workflow_yaml_path="$1"
  local yaml_dir
  yaml_dir="$(dirname "$workflow_yaml_path")"
  local yaml_file
  yaml_file="$(basename "$workflow_yaml_path")"
  echo "Starting zigflow runner for ${workflow_yaml_path}..."
  # --metrics-listen-address / --health-listen-address :0 let the OS pick free ports; zigflow's
  # fixed defaults (0.0.0.0:9090 / 0.0.0.0:3000) collide with anything else already bound to
  # those ports on the host and would otherwise make the zigflow worker fail to start with no
  # workflow ever getting served.
  (cd "$yaml_dir" && exec zigflow run -f "$yaml_file" --temporal-address "$TEMPORAL_ADDRESS" \
    --disable-telemetry --metrics-listen-address 127.0.0.1:0 --health-listen-address 127.0.0.1:0) &
  SANDBOX_WORKER_PIDS+=("$!")
  sleep 2
}

# sandbox_cleanup — registered via `trap sandbox_cleanup EXIT INT TERM` in
# each run.sh. Kills any workers/zigflow processes this script started, and
# the dev Temporal server too, but ONLY if this script started it.
sandbox_cleanup() {
  local pid
  for pid in "${SANDBOX_WORKER_PIDS[@]:-}"; do
    [ -n "$pid" ] || continue
    kill "$pid" 2>/dev/null || true
  done

  if [ "$SANDBOX_WE_STARTED_TEMPORAL" = "1" ] && [ -n "$SANDBOX_STARTED_TEMPORAL_PID" ]; then
    kill "$SANDBOX_STARTED_TEMPORAL_PID" 2>/dev/null || true
  fi
}

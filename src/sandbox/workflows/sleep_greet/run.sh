#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../_lib.sh"
trap sandbox_cleanup EXIT INT TERM

sandbox_ensure_temporal
sandbox_start_worker sleep_greet

INPUT="${1:-\"World\"}"
echo "Starting SleepGreetWorkflow on task queue sleep_greet..."
(cd "$SANDBOX_REPO_ROOT" && uv run python -m sandbox.starter SleepGreetWorkflow "$INPUT")

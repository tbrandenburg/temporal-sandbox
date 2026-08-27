#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../_lib.sh"
trap sandbox_cleanup EXIT INT TERM

sandbox_ensure_temporal
sandbox_start_worker say_hello

INPUT="${1:-\"World\"}"
echo "Starting SayHelloWorkflow on task queue say_hello..."
(cd "$SANDBOX_REPO_ROOT" && uv run python -m sandbox.starter SayHelloWorkflow "$INPUT")

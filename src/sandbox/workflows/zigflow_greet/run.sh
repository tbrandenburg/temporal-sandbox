#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../_lib.sh"
trap sandbox_cleanup EXIT INT TERM

sandbox_ensure_temporal
sandbox_start_worker zigflow_greet
sandbox_start_zigflow "$(dirname "${BASH_SOURCE[0]}")/workflow.yaml"

INPUT="${1:-{\"name\":\"Ziggy\"}}"
echo "Starting ZigflowGreetWorkflow on task queue zigflow-greet..."
(cd "$SANDBOX_REPO_ROOT" && uv run python -m sandbox.starter ZigflowGreetWorkflow "$INPUT")

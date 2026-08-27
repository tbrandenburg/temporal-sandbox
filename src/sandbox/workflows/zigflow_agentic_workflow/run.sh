#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../_lib.sh"
trap sandbox_cleanup EXIT INT TERM

sandbox_ensure_temporal
sandbox_start_worker zigflow_agentic_workflow
sandbox_start_zigflow "$(dirname "${BASH_SOURCE[0]}")/workflow.yaml"

DEFAULT_INPUT='{"question":"Who wrote The Hobbit?","maxIterations":5}'
INPUT="${1:-$DEFAULT_INPUT}"
echo "Starting agentic-workflow on task queue zigflow-agentic-workflow..."
(cd "$SANDBOX_REPO_ROOT" && uv run python -m sandbox.starter agentic-workflow "$INPUT")

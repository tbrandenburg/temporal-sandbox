#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../_lib.sh"
trap sandbox_cleanup EXIT INT TERM

sandbox_ensure_temporal
sandbox_start_zigflow "$(dirname "${BASH_SOURCE[0]}")/workflow.yaml"

echo "Starting try-catch workflow on task queue zigflow-error-handling..."
(cd "$SANDBOX_REPO_ROOT" && uv run python -m sandbox.starter try-catch '{}')

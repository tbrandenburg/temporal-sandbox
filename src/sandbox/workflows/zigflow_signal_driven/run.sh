#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../_lib.sh"
trap sandbox_cleanup EXIT INT TERM

sandbox_ensure_temporal
sandbox_start_zigflow "$(dirname "${BASH_SOURCE[0]}")/workflow.yaml"

WORKFLOW_ID="signal-demo-$(date +%s)"
echo "Starting signal workflow on task queue zigflow-signal-driven (workflow id ${WORKFLOW_ID})..."
temporal workflow start \
  --address 127.0.0.1:7233 \
  --type signal \
  --task-queue zigflow-signal-driven \
  --workflow-id "$WORKFLOW_ID"

sleep 2

echo "Sending 'approve' signal to ${WORKFLOW_ID}..."
temporal workflow signal \
  --address 127.0.0.1:7233 \
  --workflow-id "$WORKFLOW_ID" \
  --name approve \
  --input '{"approved": true}'

echo "Fetching result for ${WORKFLOW_ID}..."
temporal workflow result --address 127.0.0.1:7233 --workflow-id "$WORKFLOW_ID"

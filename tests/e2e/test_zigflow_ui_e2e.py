"""E2E scenario 5 (final): the zigflow DSL workflow executes healthily and the Web UI proves it.

This is the only test covering the full cross-runtime chain: the Go zigflow worker executes
workflow.yaml on the `zigflow-greet` queue and dispatches `shout_greet` to the Python worker
on `zigflow-greet-activities`. Asserting via the UI (not just the CLI) additionally proves
the execution is observable and correctly typed for a human operator.
"""

import json
import shutil
import subprocess
import uuid

import pytest
from playwright.sync_api import Page, expect

TEMPORAL_BIN = shutil.which("temporal") or "/home/linuxbrew/.linuxbrew/opt/temporal/bin/temporal"
DSL_TASK_QUEUE = "zigflow-greet"
WORKFLOW_TYPE = "ZigflowGreetWorkflow"


@pytest.mark.e2e
def test_ui_shows_healthy_zigflow_execution(docker_stack: dict[str, str], page: Page) -> None:
    address = docker_stack["address"]
    workflow_id = f"test-zigflow-ui-e2e-{uuid.uuid4()}"

    start_result = subprocess.run(
        [
            TEMPORAL_BIN,
            "--address",
            address,
            "workflow",
            "start",
            "--task-queue",
            DSL_TASK_QUEUE,
            "--type",
            WORKFLOW_TYPE,
            "--input",
            json.dumps({"name": "Ziggy"}),
            "--workflow-id",
            workflow_id,
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert start_result.returncode == 0, start_result.stderr

    # Block until terminal state so the UI assertions aren't racing the execution.
    wait_result = subprocess.run(
        [TEMPORAL_BIN, "--address", address, "workflow", "result", "-w", workflow_id],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert wait_result.returncode == 0, wait_result.stderr
    assert "HELLO ZIGGY" in wait_result.stdout, wait_result.stdout

    page.goto(f"{docker_stack['ui_url']}/namespaces/default/workflows/{workflow_id}")

    expect(page.get_by_test_id("workflow-status").get_by_text("Completed")).to_be_visible(
        timeout=15_000
    )
    expect(page.get_by_role("link", name=WORKFLOW_TYPE)).to_be_visible()

    page.get_by_test_id("history-tab").click()
    expect(page.get_by_text("Activity Task Completed")).to_be_visible(timeout=15_000)

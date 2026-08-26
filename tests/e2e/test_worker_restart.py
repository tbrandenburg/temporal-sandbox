"""E2E scenario 4: Durable Execution survives a hard worker kill mid-timer.

Starts a SleepGreetWorkflow (10s sleep), SIGKILLs its worker container partway through the
sleep, restarts the container, and asserts the workflow still completes. This is the only
e2e test that actually proves durability rather than asserting a string.
"""

import json
import shutil
import subprocess
import time
import uuid

import pytest

TEMPORAL_BIN = shutil.which("temporal") or "/home/linuxbrew/.linuxbrew/opt/temporal/bin/temporal"
WORKER_CONTAINER = "temporal-sandbox-worker-sleep_greet-1"
KILL_DELAY_SECONDS = 3
DESCRIBE_POLL_TIMEOUT_SECONDS = 40
DESCRIBE_POLL_INTERVAL_SECONDS = 2


def _describe(address: str, workflow_id: str) -> dict:
    result = subprocess.run(
        [
            TEMPORAL_BIN,
            "--address",
            address,
            "workflow",
            "describe",
            "-w",
            workflow_id,
            "-o",
            "json",
        ],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.mark.e2e
def test_workflow_survives_worker_kill_mid_timer(docker_stack: dict[str, str]) -> None:
    address = docker_stack["address"]
    workflow_id = f"test-restart-e2e-{uuid.uuid4()}"

    start_result = subprocess.run(
        [
            TEMPORAL_BIN,
            "--address",
            address,
            "workflow",
            "start",
            "--task-queue",
            "sleep_greet",
            "--type",
            "SleepGreetWorkflow",
            "--input",
            '"Restart"',
            "--workflow-id",
            workflow_id,
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert start_result.returncode == 0, start_result.stderr

    # Well within the 10s workflow sleep: kill the worker, then bring it back.
    time.sleep(KILL_DELAY_SECONDS)

    kill_result = subprocess.run(
        ["docker", "kill", WORKER_CONTAINER], capture_output=True, text=True, timeout=15
    )
    assert kill_result.returncode == 0, kill_result.stderr

    restart_result = subprocess.run(
        ["docker", "compose", "up", "-d", "worker-sleep_greet"],
        cwd=__import__("pathlib").Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert restart_result.returncode == 0, restart_result.stderr

    deadline = time.monotonic() + DESCRIBE_POLL_TIMEOUT_SECONDS
    describe_json = _describe(address, workflow_id)
    while describe_json["workflowExecutionInfo"]["status"] == "WORKFLOW_EXECUTION_STATUS_RUNNING":
        if time.monotonic() > deadline:
            pytest.fail(f"Workflow {workflow_id} did not complete within timeout after worker kill")
        time.sleep(DESCRIBE_POLL_INTERVAL_SECONDS)
        describe_json = _describe(address, workflow_id)

    assert describe_json["workflowExecutionInfo"]["status"] == "WORKFLOW_EXECUTION_STATUS_COMPLETED"
    assert describe_json["result"] == "Hello (after a nap) Restart"

"""E2E scenario 2: drive workflow start/result/describe via the raw temporal CLI."""

import json
import shutil
import subprocess
import uuid

import pytest

TEMPORAL_BIN = shutil.which("temporal") or "/home/linuxbrew/.linuxbrew/opt/temporal/bin/temporal"


@pytest.mark.e2e
def test_cli_start_and_describe_completed_workflow(docker_stack: dict[str, str]) -> None:
    address = docker_stack["address"]
    workflow_id = f"test-cli-e2e-{uuid.uuid4()}"

    start_result = subprocess.run(
        [
            TEMPORAL_BIN,
            "--address",
            address,
            "workflow",
            "start",
            "--task-queue",
            "say_hello",
            "--type",
            "SayHelloWorkflow",
            "--input",
            '"CLI"',
            "--workflow-id",
            workflow_id,
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert start_result.returncode == 0, start_result.stderr

    result_result = subprocess.run(
        [TEMPORAL_BIN, "--address", address, "workflow", "result", "-w", workflow_id],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result_result.returncode == 0, result_result.stderr
    assert '"Hello CLI"' in result_result.stdout

    describe_result = subprocess.run(
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
        timeout=30,
    )
    assert describe_result.returncode == 0, describe_result.stderr

    describe_json = json.loads(describe_result.stdout)
    status = describe_json["workflowExecutionInfo"]["status"]
    assert status == "WORKFLOW_EXECUTION_STATUS_COMPLETED"

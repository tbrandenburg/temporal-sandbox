"""E2E scenario 3: the Temporal Web UI renders a completed workflow correctly."""

import os
import shutil
import subprocess
import uuid

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
def test_ui_shows_completed_workflow(docker_stack: dict[str, str], page: Page) -> None:
    workflow_id = f"test-ui-e2e-{uuid.uuid4()}"
    env = os.environ | {"TEMPORAL_ADDRESS": docker_stack["address"]}
    temporal_bin = (
        shutil.which("temporal") or "/home/linuxbrew/.linuxbrew/opt/temporal/bin/temporal"
    )

    start_result = subprocess.run(
        [
            temporal_bin,
            "--address",
            docker_stack["address"],
            "workflow",
            "start",
            "--task-queue",
            "say_hello",
            "--type",
            "SayHelloWorkflow",
            "--input",
            '"UI"',
            "--workflow-id",
            workflow_id,
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert start_result.returncode == 0, start_result.stderr

    wait_result = subprocess.run(
        [
            temporal_bin,
            "--address",
            docker_stack["address"],
            "workflow",
            "result",
            "-w",
            workflow_id,
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert wait_result.returncode == 0, wait_result.stderr

    page.goto(f"{docker_stack['ui_url']}/namespaces/default/workflows/{workflow_id}")

    expect(page.get_by_test_id("workflow-status").get_by_text("Completed")).to_be_visible(
        timeout=15_000
    )
    expect(page.get_by_role("link", name="SayHelloWorkflow")).to_be_visible()

    page.get_by_test_id("history-tab").click()
    expect(page.get_by_text("Activity Task Completed")).to_be_visible(timeout=15_000)

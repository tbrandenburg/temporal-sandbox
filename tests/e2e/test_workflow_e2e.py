"""E2E scenario 1: the starter CLI executes a workflow against the real Docker stack."""

import os
import subprocess
import sys

import pytest


@pytest.mark.e2e
def test_starter_executes_say_hello_workflow(docker_stack: dict[str, str]) -> None:
    env = os.environ | {"TEMPORAL_ADDRESS": docker_stack["address"]}
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "sandbox.starter",
            "SayHelloWorkflow",
            '"Temporal"',
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "Hello Temporal"

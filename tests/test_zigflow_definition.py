"""Guards the YAML<->Python contract for the zigflow_greet bundle.

The YAML is executable config that no Python module imports, so nothing else would notice
if a task queue or activity name drifted apart. Also re-runs zigflow's own validator as a
regression guard.
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

import sandbox.workflows  # noqa: F401  (registers bundles)
from sandbox import registry

WORKFLOW_YAML = (
    Path(__file__).resolve().parents[1] / "src/sandbox/workflows/zigflow_greet/workflow.yaml"
)
# Enforced by zigflow itself; underscores are rejected in document.taskQueue.
TASK_QUEUE_PATTERN = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$")


@pytest.fixture(scope="module")
def definition() -> dict:
    return yaml.safe_load(WORKFLOW_YAML.read_text())


def test_dsl_task_queue_matches_registry(definition):
    bundle = registry.REGISTRY["zigflow_greet"]
    workflow_type = definition["document"]["workflowType"]
    assert bundle.dsl_workflows[workflow_type] == definition["document"]["taskQueue"]


def test_activity_call_matches_registered_activity(definition):
    bundle = registry.REGISTRY["zigflow_greet"]
    call = definition["do"][0]["greet"]["with"]
    assert call["taskQueue"] == bundle.effective_task_queue
    assert call["name"] in {a.__name__ for a in bundle.activities}


def test_task_queues_are_valid_for_zigflow(definition):
    bundle = registry.REGISTRY["zigflow_greet"]
    for queue in (definition["document"]["taskQueue"], bundle.effective_task_queue):
        assert TASK_QUEUE_PATTERN.match(queue), f"{queue!r} is not a legal zigflow task queue"


@pytest.mark.skipif(shutil.which("zigflow") is None, reason="zigflow CLI not installed")
def test_definition_passes_zigflow_validate():
    result = subprocess.run(
        ["zigflow", "validate", str(WORKFLOW_YAML)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr

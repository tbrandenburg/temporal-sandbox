"""Guards the YAML<->Python contract for zigflow DSL bundles.

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

WORKFLOWS_DIR = Path(__file__).resolve().parents[1] / "src/sandbox/workflows"

# Enforced by zigflow itself; underscores are rejected in document.taskQueue.
TASK_QUEUE_PATTERN = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$")

ZIGFLOW_BUNDLES = [
    "zigflow_greet",
    "zigflow_hello_world",
    "zigflow_http_call",
    "zigflow_error_handling",
    "zigflow_parallel_tasks",
    "zigflow_signal_driven",
]


def _workflow_yaml(bundle_name: str) -> Path:
    return WORKFLOWS_DIR / bundle_name / "workflow.yaml"


def _definition(bundle_name: str) -> dict:
    return yaml.safe_load(_workflow_yaml(bundle_name).read_text())


@pytest.mark.parametrize("bundle_name", ZIGFLOW_BUNDLES)
def test_dsl_task_queue_matches_registry(bundle_name):
    bundle = registry.REGISTRY[bundle_name]
    definition = _definition(bundle_name)
    workflow_type = definition["document"]["workflowType"]
    assert bundle.dsl_workflows[workflow_type] == definition["document"]["taskQueue"]


def test_activity_call_matches_registered_activity():
    bundle = registry.REGISTRY["zigflow_greet"]
    definition = _definition("zigflow_greet")
    call = definition["do"][0]["greet"]["with"]
    assert call["taskQueue"] == bundle.effective_task_queue
    assert call["name"] in {a.__name__ for a in bundle.activities}


@pytest.mark.parametrize("bundle_name", ZIGFLOW_BUNDLES)
def test_task_queues_are_valid_for_zigflow(bundle_name):
    bundle = registry.REGISTRY[bundle_name]
    definition = _definition(bundle_name)
    for queue in (definition["document"]["taskQueue"], bundle.effective_task_queue):
        assert TASK_QUEUE_PATTERN.match(queue), f"{queue!r} is not a legal zigflow task queue"


@pytest.mark.skipif(shutil.which("zigflow") is None, reason="zigflow CLI not installed")
@pytest.mark.parametrize("bundle_name", ZIGFLOW_BUNDLES)
def test_definition_passes_zigflow_validate(bundle_name):
    result = subprocess.run(
        ["zigflow", "validate", str(_workflow_yaml(bundle_name))],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr

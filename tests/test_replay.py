"""Replay determinism guard: runs committed event history fixtures through Replayer.

Fixtures under tests/histories/*.json are real event histories exported via
`temporal workflow show -w <id> -o json` against a live workflow execution. If current
workflow code has diverged from what actually produced that history, replay raises a
non-determinism error and this test fails.

Regenerate fixtures with `make record-history` (requires `make up` first).
"""

from pathlib import Path

import pytest
from temporalio.client import WorkflowHistory
from temporalio.worker import Replayer

from sandbox.workflows.say_hello.workflow import SayHelloWorkflow
from sandbox.workflows.sleep_greet.workflow import SleepGreetWorkflow

HISTORIES_DIR = Path(__file__).parent / "histories"


@pytest.mark.parametrize(
    ("workflow_cls", "workflow_id", "history_file"),
    [
        (SayHelloWorkflow, "replay-say-hello", "say_hello.json"),
        (SleepGreetWorkflow, "replay-sleep-greet", "sleep_greet.json"),
    ],
)
async def test_replay_does_not_detect_non_determinism(workflow_cls, workflow_id, history_file):
    history_json = (HISTORIES_DIR / history_file).read_text()
    history = WorkflowHistory.from_json(workflow_id, history_json)
    replayer = Replayer(workflows=[workflow_cls])
    await replayer.replay_workflow(history)

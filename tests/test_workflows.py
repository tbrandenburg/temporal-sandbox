import uuid

from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from sandbox.workflows.say_hello.activities import greet
from sandbox.workflows.say_hello.workflow import SayHelloWorkflow
from sandbox.workflows.sleep_greet.activities import greet as sleep_greet_greet
from sandbox.workflows.sleep_greet.workflow import SleepGreetWorkflow


async def test_say_hello_workflow():
    task_queue = str(uuid.uuid4())
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue=task_queue,
            workflows=[SayHelloWorkflow],
            activities=[greet],
        ):
            result = await env.client.execute_workflow(
                SayHelloWorkflow.run,
                "Temporal",
                id=str(uuid.uuid4()),
                task_queue=task_queue,
            )
            assert result == "Hello Temporal"


async def test_sleep_greet_workflow():
    # start_time_skipping() skips the workflow.sleep() timer instantly, so this test stays fast
    # despite SleepGreetWorkflow.SLEEP_SECONDS being tuned for a real-wall-clock e2e test.
    task_queue = str(uuid.uuid4())
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue=task_queue,
            workflows=[SleepGreetWorkflow],
            activities=[sleep_greet_greet],
        ):
            result = await env.client.execute_workflow(
                SleepGreetWorkflow.run,
                "Temporal",
                id=str(uuid.uuid4()),
                task_queue=task_queue,
            )
            assert result == "Hello (after a nap) Temporal"

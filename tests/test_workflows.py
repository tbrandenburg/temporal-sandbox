import uuid

from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from sandbox.workflows.say_hello.activities import greet
from sandbox.workflows.say_hello.workflow import SayHelloWorkflow


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

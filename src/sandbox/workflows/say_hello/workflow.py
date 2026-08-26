from datetime import timedelta

from temporalio import workflow

from sandbox.registry import Bundle, register

with workflow.unsafe.imports_passed_through():
    from sandbox.workflows.say_hello.activities import greet


@workflow.defn
class SayHelloWorkflow:
    @workflow.run
    async def run(self, name: str) -> str:
        return await workflow.execute_activity(
            greet, name, start_to_close_timeout=timedelta(seconds=10)
        )


register(Bundle(name="say_hello", workflows=[SayHelloWorkflow], activities=[greet]))

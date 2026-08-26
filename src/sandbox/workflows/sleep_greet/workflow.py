from datetime import timedelta

from temporalio import workflow

from sandbox.registry import Bundle, register

with workflow.unsafe.imports_passed_through():
    from sandbox.workflows.sleep_greet.activities import greet

# Long enough for a human/script to `docker kill` the worker mid-sleep during the future
# worker-restart e2e test (step 8), short enough not to slow down integration tests where
# start_time_skipping() skips it instantly anyway.
SLEEP_SECONDS = 10


@workflow.defn
class SleepGreetWorkflow:
    @workflow.run
    async def run(self, name: str) -> str:
        await workflow.sleep(timedelta(seconds=SLEEP_SECONDS))
        return await workflow.execute_activity(
            greet, name, start_to_close_timeout=timedelta(seconds=10)
        )


register(Bundle(name="sleep_greet", workflows=[SleepGreetWorkflow], activities=[greet]))

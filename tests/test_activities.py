from temporalio.testing import ActivityEnvironment

from sandbox.workflows.say_hello.activities import greet


async def test_greet():
    env = ActivityEnvironment()
    result = await env.run(greet, "World")
    assert result == "Hello World"

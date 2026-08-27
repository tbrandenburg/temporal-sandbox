from temporalio.testing import ActivityEnvironment

from sandbox.workflows.say_hello.activities import greet as say_hello_greet
from sandbox.workflows.sleep_greet.activities import greet as sleep_greet_greet
from sandbox.workflows.zigflow_greet.activities import shout_greet


async def test_greet():
    env = ActivityEnvironment()
    result = await env.run(say_hello_greet, "World")
    assert result == "Hello World"


async def test_sleep_greet_activity():
    env = ActivityEnvironment()
    result = await env.run(sleep_greet_greet, "World")
    assert result == "Hello (after a nap) World"


async def test_shout_greet_activity():
    env = ActivityEnvironment()
    result = await env.run(shout_greet, "World")
    assert result == "HELLO WORLD"

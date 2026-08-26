"""Importing this package triggers register() side effects for every bundle."""

from sandbox.workflows.say_hello import workflow as _say_hello_workflow
from sandbox.workflows.sleep_greet import workflow as _sleep_greet_workflow

__all__ = ["_say_hello_workflow", "_sleep_greet_workflow"]

"""Importing this package triggers register() side effects for every bundle."""

from sandbox.workflows.say_hello import workflow as _say_hello_workflow

__all__ = ["_say_hello_workflow"]

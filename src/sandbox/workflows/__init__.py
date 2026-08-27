"""Importing this package triggers register() side effects for every bundle."""

from sandbox.workflows import zigflow_agentic_workflow as _zigflow_agentic_workflow_bundle
from sandbox.workflows import zigflow_error_handling as _zigflow_error_handling_bundle
from sandbox.workflows import zigflow_greet as _zigflow_greet_bundle
from sandbox.workflows import zigflow_hello_world as _zigflow_hello_world_bundle
from sandbox.workflows import zigflow_http_call as _zigflow_http_call_bundle
from sandbox.workflows import zigflow_parallel_tasks as _zigflow_parallel_tasks_bundle
from sandbox.workflows import zigflow_signal_driven as _zigflow_signal_driven_bundle
from sandbox.workflows.say_hello import workflow as _say_hello_workflow
from sandbox.workflows.sleep_greet import workflow as _sleep_greet_workflow

__all__ = [
    "_say_hello_workflow",
    "_sleep_greet_workflow",
    "_zigflow_agentic_workflow_bundle",
    "_zigflow_greet_bundle",
    "_zigflow_hello_world_bundle",
    "_zigflow_http_call_bundle",
    "_zigflow_error_handling_bundle",
    "_zigflow_parallel_tasks_bundle",
    "_zigflow_signal_driven_bundle",
]

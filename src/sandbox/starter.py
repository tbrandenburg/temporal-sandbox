"""python -m sandbox.starter <WorkflowName> <json-arg> — start a workflow and print its result.

Task queue resolution: iterate registered bundles and match by workflow class `__name__`.
Falls back to a bundle's `dsl_workflows` mapping for workflows executed by the zigflow DSL
engine rather than a Python worker. Simplest approach that keeps worker.py/starter.py in
lockstep without an extra CLI flag.
"""

import argparse
import asyncio
import json
import uuid

from temporalio.client import Client

import sandbox.workflows  # noqa: F401  (side effect: registers all bundles)
from sandbox import config, registry


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start a Temporal sandbox workflow.")
    parser.add_argument("workflow", help="Workflow class name, e.g. SayHelloWorkflow")
    parser.add_argument("arg", help="Single JSON-encoded argument passed to the workflow")
    return parser.parse_args()


def find_task_queue(workflow_name: str) -> str:
    for bundle in registry.REGISTRY.values():
        if any(wf.__name__ == workflow_name for wf in bundle.workflows):
            return bundle.effective_task_queue
        if workflow_name in bundle.dsl_workflows:
            return bundle.dsl_workflows[workflow_name]
    known = [wf.__name__ for bundle in registry.REGISTRY.values() for wf in bundle.workflows]
    known += [name for bundle in registry.REGISTRY.values() for name in bundle.dsl_workflows]
    raise ValueError(f"Unknown workflow {workflow_name!r}; known workflows: {', '.join(known)}")


async def main() -> None:
    args = parse_args()
    workflow_arg = json.loads(args.arg)
    task_queue = find_task_queue(args.workflow)

    client = await Client.connect(config.TEMPORAL_ADDRESS, namespace=config.TEMPORAL_NAMESPACE)
    result = await client.execute_workflow(
        args.workflow,
        workflow_arg,
        id=f"{args.workflow}-{uuid.uuid4()}",
        task_queue=task_queue,
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())

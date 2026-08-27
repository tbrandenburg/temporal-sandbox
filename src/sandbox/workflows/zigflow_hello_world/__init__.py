from sandbox.registry import Bundle, register

# Pure zigflow DSL example (docs: https://zigflow.dev/docs/examples/hello-world).
# No Python workflow class or activity: the workflow lives entirely in workflow.yaml,
# executed by a separate `zigflow run` process. This bundle only registers task-queue
# metadata so `make run`/starter.py can resolve the workflow type to a task queue.
register(
    Bundle(
        name="zigflow_hello_world",
        dsl_workflows={"hello-world": "zigflow-hello-world"},
        task_queue="zigflow-hello-world",
    )
)

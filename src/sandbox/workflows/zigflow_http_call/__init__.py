from sandbox.registry import Bundle, register

# Pure zigflow DSL example (docs: https://zigflow.dev/docs/examples/http-call).
# No Python workflow class or activity: the workflow lives entirely in workflow.yaml,
# executed by a separate `zigflow run` process. This bundle only registers task-queue
# metadata so `make run`/starter.py can resolve the workflow type to a task queue.
register(
    Bundle(
        name="zigflow_http_call",
        dsl_workflows={"fetch-user": "zigflow-http-call"},
        task_queue="zigflow-http-call",
    )
)

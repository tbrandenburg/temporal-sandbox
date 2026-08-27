from sandbox.registry import Bundle, register

# Pure zigflow DSL example (docs: https://zigflow.dev/docs/examples/error-handling).
# No Python workflow class or activity: the workflow lives entirely in workflow.yaml,
# executed by a separate `zigflow run` process. This bundle only registers task-queue
# metadata so `make run`/starter.py can resolve the workflow type to a task queue.
register(
    Bundle(
        name="zigflow_error_handling",
        dsl_workflows={"try-catch": "zigflow-error-handling"},
        task_queue="zigflow-error-handling",
    )
)

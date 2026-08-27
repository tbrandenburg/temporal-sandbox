from sandbox.registry import Bundle, register
from sandbox.workflows.zigflow_greet.activities import shout_greet

DSL_TASK_QUEUE = "zigflow-greet"
ACTIVITY_TASK_QUEUE = "zigflow-greet-activities"

# No Python workflow class: the workflow lives in workflow.yaml and is executed by the
# zigflow DSL worker (separate process/container). This bundle contributes the activity only.
register(
    Bundle(
        name="zigflow_greet",
        activities=[shout_greet],
        dsl_workflows={"ZigflowGreetWorkflow": DSL_TASK_QUEUE},
        task_queue=ACTIVITY_TASK_QUEUE,
    )
)

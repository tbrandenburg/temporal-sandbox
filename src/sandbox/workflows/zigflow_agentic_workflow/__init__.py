from sandbox.registry import Bundle, register
from sandbox.workflows.zigflow_agentic_workflow.activities import (
    lookup,
    plan_next_step,
    summarise_partial_result,
)

DSL_TASK_QUEUE = "zigflow-agentic-workflow"
ACTIVITY_TASK_QUEUE = "zigflow-agentic-workflow-activities"

# No Python workflow class: the workflow lives in workflow.yaml and is executed by the
# zigflow DSL worker (separate process/container). This bundle contributes the activities only.
#
# NOTE: because workflow.yaml's top-level `do:` block is a multi-task state machine
# (agentic-workflow / runLookup / markAnswered / markUnsupported / summarisePartialResult, wired
# together via `switch.then` jumps) rather than a flat list of steps, zigflow registers each
# top-level task name as its own callable Temporal workflow type, and the entry point actually
# invocable via `client.execute_workflow` is the first one: "agentic-workflow" (verified
# empirically end-to-end). `document.workflowType` is set to match this so the
# test_zigflow_definition.py contract check (`dsl_workflows[workflowType] == taskQueue`) holds.
register(
    Bundle(
        name="zigflow_agentic_workflow",
        activities=[plan_next_step, lookup, summarise_partial_result],
        dsl_workflows={"agentic-workflow": DSL_TASK_QUEUE},
        task_queue=ACTIVITY_TASK_QUEUE,
    )
)

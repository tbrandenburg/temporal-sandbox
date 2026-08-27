from unittest.mock import patch

from temporalio.testing import ActivityEnvironment

from sandbox.workflows.zigflow_agentic_workflow.activities import (
    lookup,
    plan_next_step,
    summarise_partial_result,
)

MODULE = "sandbox.workflows.zigflow_agentic_workflow.activities"


async def test_plan_next_step_uses_valid_lookup_plan():
    env = ActivityEnvironment()
    req = {"question": "What is the capital of France?", "observations": [], "iteration": 0}
    with patch(f"{MODULE}._call_big_pickle") as mock_call:
        mock_call.return_value = {"tool": "lookup", "arguments": {"query": "capital of France"}}
        result = await env.run(plan_next_step, req)
    assert result == {"tool": "lookup", "arguments": {"query": "capital of France"}}


async def test_plan_next_step_uses_valid_final_answer_plan():
    env = ActivityEnvironment()
    req = {"question": "What is the capital of France?", "observations": [], "iteration": 1}
    with patch(f"{MODULE}._call_big_pickle") as mock_call:
        mock_call.return_value = {"tool": "final_answer", "arguments": {"answer": "Paris"}}
        result = await env.run(plan_next_step, req)
    assert result == {"tool": "final_answer", "arguments": {"answer": "Paris"}}


async def test_plan_next_step_falls_back_to_lookup_when_no_observations():
    env = ActivityEnvironment()
    req = {"question": "What is the capital of France?", "observations": [], "iteration": 0}
    with patch(f"{MODULE}._call_big_pickle") as mock_call:
        mock_call.return_value = None
        result = await env.run(plan_next_step, req)
    assert result == {
        "tool": "lookup",
        "arguments": {"query": "What is the capital of France?"},
    }


async def test_plan_next_step_falls_back_to_final_answer_when_observations_present():
    env = ActivityEnvironment()
    observations = [
        {"output": {"answer": "Paris"}},
        {"output": {"answer": "Also Paris"}},
    ]
    req = {
        "question": "What is the capital of France?",
        "observations": observations,
        "iteration": 2,
    }
    with patch(f"{MODULE}._call_big_pickle") as mock_call:
        mock_call.return_value = None
        result = await env.run(plan_next_step, req)
    assert result["tool"] == "final_answer"
    assert "2" in result["arguments"]["answer"]
    assert "Based on 2 lookup(s)" in result["arguments"]["answer"]


async def test_plan_next_step_guardrails_missing_query():
    env = ActivityEnvironment()
    req = {"question": "What is the capital of France?", "observations": [], "iteration": 0}
    with patch(f"{MODULE}._call_big_pickle") as mock_call:
        mock_call.return_value = {"tool": "lookup", "arguments": {}}
        result = await env.run(plan_next_step, req)
    assert result == {
        "tool": "lookup",
        "arguments": {"query": "What is the capital of France?"},
    }


async def test_plan_next_step_guardrails_bogus_tool():
    env = ActivityEnvironment()
    observations = [{"output": {"answer": "Paris"}}]
    req = {
        "question": "What is the capital of France?",
        "observations": observations,
        "iteration": 1,
    }
    with patch(f"{MODULE}._call_big_pickle") as mock_call:
        mock_call.return_value = {"tool": "bogus"}
        result = await env.run(plan_next_step, req)
    assert result["tool"] == "final_answer"
    assert "1" in result["arguments"]["answer"]


async def test_plan_next_step_guardrails_arguments_not_a_dict():
    env = ActivityEnvironment()
    req = {"question": "What is the capital of France?", "observations": [], "iteration": 0}
    with patch(f"{MODULE}._call_big_pickle") as mock_call:
        mock_call.return_value = {"tool": "lookup", "arguments": "capital of France"}
        result = await env.run(plan_next_step, req)
    assert result == {
        "tool": "lookup",
        "arguments": {"query": "What is the capital of France?"},
    }


async def test_lookup_returns_big_pickle_answer():
    env = ActivityEnvironment()
    with patch(f"{MODULE}._call_big_pickle") as mock_call:
        mock_call.return_value = {"answer": "Paris is great."}
        result = await env.run(lookup, {"query": "capital of France"})
    assert result == {"answer": "Paris is great.", "source": "big-pickle"}


async def test_lookup_falls_back_when_big_pickle_unavailable():
    env = ActivityEnvironment()
    with patch(f"{MODULE}._call_big_pickle") as mock_call:
        mock_call.return_value = None
        result = await env.run(lookup, {"query": "capital of France"})
    assert result == {"answer": "I am unsure.", "source": "fallback:unavailable"}


async def test_lookup_blank_answer_falls_back_to_unsure_text():
    env = ActivityEnvironment()
    with patch(f"{MODULE}._call_big_pickle") as mock_call:
        mock_call.return_value = {"answer": "   "}
        result = await env.run(lookup, {"query": "capital of France"})
    # NOTE: source is still "big-pickle" here because the call itself succeeded;
    # only the answer content was blank. See handoff "Follow-up issues found".
    assert result == {"answer": "I am unsure.", "source": "big-pickle"}


async def test_summarise_partial_result_mentions_count_and_question():
    env = ActivityEnvironment()
    req = {
        "observations": [{"output": {"answer": "a"}}, {"output": {"answer": "b"}}],
        "question": "What is the capital of France?",
    }
    result = await env.run(summarise_partial_result, req)
    assert "2" in result["answer"]
    assert "What is the capital of France?" in result["answer"]

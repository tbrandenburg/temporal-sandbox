import json
import urllib.error
import urllib.request

from temporalio import activity

BIG_PICKLE_URL = "https://opencode.ai/zen/v1/chat/completions"
BIG_PICKLE_MODEL = "big-pickle"
BIG_PICKLE_TIMEOUT_SECONDS = 30

PLAN_SYSTEM_PROMPT = """You are a tiny ReAct planning agent.
You are given a question and a list of past observations from tool calls.
You must decide the next single action.

Tools:
- "lookup":       call a factual lookup tool. Arguments: { "query": "<short factual question>" }
- "final_answer": when the observations let you answer. Arguments: { "answer": "<short answer>" }

Guidance:
- Prefer "lookup" when the observations do not yet contain the fact you need.
- Prefer "final_answer" once one or two observations cover the question.
- If the question has multiple parts, use one lookup per part.

Reply only with JSON in this exact shape, no prose:
{ "tool": "lookup" | "final_answer", "arguments": { ... } }"""

LOOKUP_SYSTEM_PROMPT = """You are a tiny factual lookup tool.
Answer the user's question in one short factual sentence.
If you are not sure, say "I am unsure.".
Reply only with JSON in the shape: { "answer": "<one short sentence>" }"""


def _call_big_pickle(system_prompt: str, user_prompt: str) -> dict | None:
    """Call the big-pickle chat completion endpoint and parse the JSON content.

    Returns None on any error (network, non-2xx, decode failure, missing keys)
    so callers can apply deterministic fallback behavior.
    """
    payload = {
        "model": BIG_PICKLE_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
    }
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        BIG_PICKLE_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            # Cloudflare rejects the default urllib User-Agent with a 403;
            # any non-default UA passes.
            "User-Agent": "temporal-sandbox/zigflow-agentic-workflow",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=BIG_PICKLE_TIMEOUT_SECONDS) as response:
            response_body = response.read()
    except (urllib.error.URLError, TimeoutError) as exc:
        activity.logger.info(f"big-pickle call failed: {exc}")
        return None

    try:
        response_json = json.loads(response_body)
        content = response_json["choices"][0]["message"]["content"]
        return json.loads(content)
    except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        activity.logger.info(f"big-pickle response parse failed: {exc}")
        return None


def _try_big_pickle_plan(req: dict) -> dict | None:
    question = req.get("question", "")
    observations = req.get("observations", [])
    iteration = req.get("iteration", 0)
    user_prompt = (
        f"Question: {question}\nObservations: {json.dumps(observations)}\nIteration: {iteration}"
    )
    raw = _call_big_pickle(PLAN_SYSTEM_PROMPT, user_prompt)
    if raw is None:
        return None

    tool = raw.get("tool")
    arguments = raw.get("arguments")
    if not isinstance(arguments, dict):
        return None

    if tool == "lookup" and isinstance(arguments.get("query"), str) and arguments["query"]:
        return {"tool": "lookup", "arguments": {"query": arguments["query"]}}
    if tool == "final_answer" and isinstance(arguments.get("answer"), str) and arguments["answer"]:
        return {"tool": "final_answer", "arguments": {"answer": arguments["answer"]}}
    return None


def _synthesise_from_observations(req: dict) -> str:
    observations = req.get("observations", [])
    question = req.get("question", "")
    if not observations:
        return "I am unsure."

    last = observations[-1]
    output = last.get("output", {})
    if isinstance(output, dict):
        answer = output.get("answer")
        if isinstance(answer, str) and answer:
            return f"Based on {len(observations)} lookup(s): {answer}"
    return f"Best-effort answer based on {len(observations)} observation(s) for: {question}"


@activity.defn(name="agent.PlanNextStep")
async def plan_next_step(req: dict) -> dict:
    observations = req.get("observations", [])
    iteration = req.get("iteration", 0)
    activity.logger.info(
        f"planning next step: iteration={iteration} observations={len(observations)}"
    )

    plan = _try_big_pickle_plan(req)
    if plan is not None:
        activity.logger.info("using planner output")
        return plan

    activity.logger.info("falling back to deterministic plan")
    if not observations:
        return {"tool": "lookup", "arguments": {"query": req.get("question", "")}}
    return {"tool": "final_answer", "arguments": {"answer": _synthesise_from_observations(req)}}


@activity.defn(name="agent.Lookup")
async def lookup(req: dict) -> dict:
    query = req.get("query", "")
    raw = _call_big_pickle(LOOKUP_SYSTEM_PROMPT, query)
    if raw is None:
        activity.logger.info("lookup falling back: big-pickle unavailable")
        return {"answer": "I am unsure.", "source": "fallback:unavailable"}

    answer = raw.get("answer")
    answer = answer.strip() if isinstance(answer, str) else ""
    if not answer:
        answer = "I am unsure."
    return {"answer": answer, "source": "big-pickle"}


@activity.defn(name="agent.SummarisePartialResult")
async def summarise_partial_result(req: dict) -> dict:
    observations = req.get("observations", [])
    question = req.get("question", "")
    answer = (
        f"I could not complete the agent loop, but I gathered "
        f"{len(observations)} observation(s) for: {question}"
    )
    return {"answer": answer}

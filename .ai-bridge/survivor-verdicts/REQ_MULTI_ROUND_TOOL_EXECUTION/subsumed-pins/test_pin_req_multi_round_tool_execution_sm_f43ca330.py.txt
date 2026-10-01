# mutation-pin: REQ_MULTI_ROUND_TOOL_EXECUTION SM-F43CA330
# pinned-by: claude-opus-5-5
from __future__ import annotations

import json

import pytest

from llm_router import LLMRouter, Model, Provider, RouterProfile
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import openai_chat_path
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk

pytestmark = pytest.mark.verification_kind("unit")


def add(a: int, b: int) -> str:
    """Add two numbers."""
    return f"first-marker-{a + b}01"


def multiply(a: int, b: int) -> str:
    """Multiply two numbers."""
    return f"second-marker-{a * b}02"


def _call(call_id: str, name: str, args: dict[str, int]) -> dict[str, object]:
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(args)},
    }


def _completion(message: dict[str, object], finish: str) -> bytes:
    body = {
        "id": "chatcmpl-1",
        "object": "chat.completion",
        "created": 0,
        "model": "m",
        "choices": [{"index": 0, "message": message, "finish_reason": finish}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10},
    }
    return json.dumps(body).encode()


@pytest.mark.verifies("REQ_MULTI_ROUND_TOOL_EXECUTION[revision==1]")
def test_two_tool_calls_in_one_round_both_results_fed_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = "neutral-auth-value"
    monkeypatch.setenv("OPENROUTER_API_KEY_1", value)
    path = openai_chat_path()
    headers = {"Content-Type": "application/json"}
    first = _completion(
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                _call("call_a", "add", {"a": 20, "b": 1}),
                _call("call_b", "multiply", {"a": 4, "b": 21}),
            ],
        },
        "tool_calls",
    )
    final = _completion({"role": "assistant", "content": "done 84"}, "stop")
    routes = {
        ("POST", path): [
            ScriptedResponse(status_code=200, headers=headers, body=first),
            ScriptedResponse(status_code=200, headers=headers, body=final),
        ]
    }
    router = LLMRouter(
        RouterProfile(provider=Provider.OPENROUTER, model=Model.DEEPSEEK_V3),
        temperature=0.0,
        seed=42,
        tools=[add, multiply],
    )
    with ScriptedHTTPServer(port=0, routes=routes) as server:
        with patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ):
            response = router.query("Compute.")
        recorded = server.recorded_requests("POST", path)
        server.retain_current_boundary_evidence()

    assert len(recorded) == 2
    assert len(response.tool_trace) == 2
    second_text = repr(recorded[1])
    assert "first-marker-2101" in second_text
    assert "second-marker-8402" in second_text

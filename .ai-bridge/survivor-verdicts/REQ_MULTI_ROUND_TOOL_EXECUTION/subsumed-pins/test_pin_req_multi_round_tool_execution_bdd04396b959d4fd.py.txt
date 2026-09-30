# mutation-pin: REQ_MULTI_ROUND_TOOL_EXECUTION bdd04396b959d4fd
# pinned-by: claude-opus-5-5
from __future__ import annotations

import json

import pytest

from llm_router import LLMRouter, Model, Provider, RouterProfile
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import openai_chat_path
from tests.llm_router.support.workers.tool_failure import openai_tool_call_response
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk

pytestmark = pytest.mark.verification_kind("unit")


def add(*, a: int, b: int) -> dict[str, int]:
    return {"value": a + b}


def multiply(*, a: int, b: int) -> dict[str, int]:
    return {"value": a * b}


def _final_text_response_body(*, text: str) -> bytes:
    payload = {
        "id": "chatcmpl-final-84",
        "object": "chat.completion",
        "created": 1700000000,
        "model": "deepseek-v3",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 12,
            "completion_tokens": 3,
            "total_tokens": 15,
        },
    }
    return json.dumps(payload).encode("utf-8")


@pytest.mark.verifies("REQ_MULTI_ROUND_TOOL_EXECUTION[revision==1]")
def test_openai_compatible_executes_add_then_multiply_to_84(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = "neutral-auth-value"
    monkeypatch.setenv("OPENROUTER_API_KEY_1", value)
    path = openai_chat_path()
    routes = {
        ("POST", path): [
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=openai_tool_call_response(
                    tool_name="add",
                    args={"a": 3, "b": 4},
                ),
            ),
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=openai_tool_call_response(
                    tool_name="multiply",
                    args={"a": 7, "b": 12},
                ),
            ),
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=_final_text_response_body(text="84"),
            ),
        ]
    }
    router = LLMRouter(
        RouterProfile(
            provider=Provider.OPENROUTER,
            model=Model.DEEPSEEK_V3,
        ),
        temperature=0.0,
        seed=42,
        tools=[add, multiply],
    )
    with ScriptedHTTPServer(port=0, routes=routes) as server:
        with patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ):
            response = router.query("Add three and four, then multiply by twelve.")
        recorded_requests = server.recorded_requests("POST", path)
        request_count = server.request_count("POST", path)
        server.retain_current_boundary_evidence()

    assert request_count == 3
    assert len(recorded_requests) == 3
    assert response.tool_calls == []
    assert response.output_text == "84"
    assert len(response.tool_trace) == 2
    first_step = response.tool_trace[0]
    second_step = response.tool_trace[1]
    assert first_step.tool_name == "add"
    assert first_step.args == {"a": 3, "b": 4}
    assert first_step.result == {"value": 7}
    assert second_step.tool_name == "multiply"
    assert second_step.args == {"a": 7, "b": 12}
    assert second_step.result == {"value": 84}

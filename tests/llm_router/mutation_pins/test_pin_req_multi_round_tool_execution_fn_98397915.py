# mutation-pin: REQ_MULTI_ROUND_TOOL_EXECUTION FN-98397915
# pinned-by: delegate, one pin for 4 pins of _advance_tool_result
# kills: 9a1e3f3eefc3663d SM-99B5EBCC SM-F43CA330 c64b7deb7394ba40
from __future__ import annotations

import json

import pytest
from pydantic import BaseModel

from llm_router import LLMRouter, Model, Provider, RouterProfile
from tests.llm_router.support.fault_server import (
    ScriptedHTTPServer,
    ScriptedResponse,
)
from tests.llm_router.support.workers.retry import openai_chat_path
from tests.llm_router.support.workers.tool_failure import (
    openai_tool_call_response,
)
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk

pytestmark = pytest.mark.verification_kind("unit")


class StructuredOutput(BaseModel):
    value: int


def add(a: int, b: int) -> str:
    """Add two numbers."""
    return f"first-marker-{a + b}01"


def multiply(a: int, b: int) -> str:
    """Multiply two numbers."""
    return f"second-marker-{a * b}02"


def build_call(call_id: str, name: str, args: dict[str, int]) -> dict[str, object]:
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(args)},
    }


def build_completion(message: dict[str, object], finish: str) -> bytes:
    body = {
        "id": "chatcmpl-1",
        "object": "chat.completion",
        "created": 0,
        "model": "m",
        "choices": [{"index": 0, "message": message, "finish_reason": finish}],
        "usage": {
            "prompt_tokens": 5,
            "completion_tokens": 5,
            "total_tokens": 10,
        },
    }
    return json.dumps(body).encode()


@pytest.fixture
def router(monkeypatch: pytest.MonkeyPatch) -> LLMRouter:
    value = "neutral-auth-value"
    monkeypatch.setenv("OPENROUTER_API_KEY_1", value)
    return LLMRouter(
        RouterProfile(
            provider=Provider.OPENROUTER,
            model=Model.DEEPSEEK_V3,
        ),
        temperature=0.0,
        seed=42,
    )


@pytest.mark.verifies("REQ_MULTI_ROUND_TOOL_EXECUTION[revision==1]")
def test_tool_call_without_registry_returns_public_response(
    router: LLMRouter,
) -> None:
    path = openai_chat_path()
    routes = {
        ("POST", path): [
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=openai_tool_call_response(
                    tool_name="add",
                    args={"a": 2, "b": 3},
                ),
            ),
        ]
    }
    with ScriptedHTTPServer(port=0, routes=routes) as server:
        with patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ):
            response = router.query(
                "Trigger tool call without registry.",
                response_schema=StructuredOutput,
            )
        recorded_requests = server.recorded_requests("POST", path)
        request_count = server.request_count("POST", path)
        server.retain_current_boundary_evidence()

    assert request_count == 1
    assert len(recorded_requests) == 1
    assert len(response.tool_calls) == 1
    tool_call = next(iter(response.tool_calls))
    assert tool_call.name == "add"
    assert tool_call.args == {"a": 2, "b": 3}
    assert response.tool_trace == []


@pytest.mark.verifies("REQ_MULTI_ROUND_TOOL_EXECUTION[revision==1]")
def test_multi_round_tool_limit_and_feedback(
    router: LLMRouter,
) -> None:
    path = openai_chat_path()
    headers = {"Content-Type": "application/json"}
    first = build_completion(
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                build_call("call_a", "add", {"a": 20, "b": 1}),
                build_call("call_b", "multiply", {"a": 4, "b": 21}),
            ],
        },
        "tool_calls",
    )
    second = build_completion(
        {
            "role": "assistant",
            "content": "Calling add again.",
            "tool_calls": [
                build_call("call_c", "add", {"a": 1, "b": 2}),
            ],
        },
        "tool_calls",
    )
    third = build_completion(
        {"role": "assistant", "content": "done 84"},
        "stop",
    )
    routes = {
        ("POST", path): [
            ScriptedResponse(status_code=200, headers=headers, body=first),
            ScriptedResponse(status_code=200, headers=headers, body=second),
            ScriptedResponse(status_code=200, headers=headers, body=third),
        ]
    }
    with ScriptedHTTPServer(port=0, routes=routes) as server:
        with patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ):
            response = router.query(
                "Compute arithmetic workflow.",
                tools=[add, multiply],
                max_tool_rounds=2,
            )
        recorded = server.recorded_requests("POST", path)
        request_count = server.request_count("POST", path)
        server.retain_current_boundary_evidence()

    assert request_count == 2
    assert len(recorded) == 2
    second_text = repr(recorded[1])
    assert "first-marker-2101" in second_text
    assert "second-marker-8402" in second_text
    assert response.output_text == ""
    assert len(response.tool_calls) == 1
    tool_call = next(iter(response.tool_calls))
    assert tool_call.name == "add"
    assert tool_call.args == {"a": 1, "b": 2}
    assert len(response.tool_trace) == 3

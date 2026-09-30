# mutation-pin: REQ_REQUEST_OVERRIDE_PRECEDENCE 02b906cf3d4b778c
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import json

import pytest

from llm_router import LLMRouter, Model, Provider, RouterProfile
from tests.llm_router.support.fault_server import (
    ScriptedHTTPServer,
    ScriptedResponse,
)
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
)
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk

pytestmark = pytest.mark.verification_kind("unit")


def add(*, a: int, b: int) -> dict[str, int]:
    """Return a+b as JSON."""
    return {"result": a + b}


def _tool_call_body() -> bytes:
    payload = json.loads(openai_success_response(text=""))
    payload["choices"][0]["message"]["tool_calls"] = [
        {
            "id": "call_add",
            "type": "function",
            "function": {"name": "add", "arguments": json.dumps({"a": 7, "b": 6})},
        }
    ]
    payload["choices"][0]["finish_reason"] = "tool_calls"
    return json.dumps(payload).encode("utf-8")


@pytest.mark.verifies("REQ_REQUEST_OVERRIDE_PRECEDENCE[revision==1]")
def test_route_default_for_other_field_keeps_default_tool_rounds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "route-credential")
    routes = {
        ("POST", openai_chat_path()): [
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=_tool_call_body(),
            ),
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=openai_success_response(text="sum is 13"),
            ),
        ]
    }
    router = LLMRouter(
        RouterProfile(provider=Provider.OPENROUTER, model=Model.DEEPSEEK_V3, seed=7),
        temperature=0.5,
    )

    with (
        ScriptedHTTPServer(port=0, routes=routes) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ),
    ):
        response = router.query("Add 7 and 6.", tools=[add])

    assert response.output_text == "sum is 13"
    assert len(response.tool_trace) == 1
    assert next(iter(response.tool_trace)).tool_name == "add"

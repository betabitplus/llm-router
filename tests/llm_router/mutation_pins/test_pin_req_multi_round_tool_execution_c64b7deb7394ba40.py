# mutation-pin: REQ_MULTI_ROUND_TOOL_EXECUTION c64b7deb7394ba40
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest
from pydantic import BaseModel

from llm_router import LLMRouter, Model, Provider, RouterProfile
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import openai_chat_path
from tests.llm_router.support.workers.tool_failure import openai_tool_call_response
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk

pytestmark = pytest.mark.verification_kind("unit")


class StructuredOutput(BaseModel):
    value: int


@pytest.mark.verifies("REQ_MULTI_ROUND_TOOL_EXECUTION[revision==1]")
def test_tool_call_without_registry_returns_public_response(
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
                    args={"a": 2, "b": 3},
                ),
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
    )
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

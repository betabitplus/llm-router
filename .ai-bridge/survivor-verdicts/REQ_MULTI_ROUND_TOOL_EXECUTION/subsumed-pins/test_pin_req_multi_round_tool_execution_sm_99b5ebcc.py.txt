# mutation-pin: REQ_MULTI_ROUND_TOOL_EXECUTION SM-99B5EBCC
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

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


def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


@pytest.mark.verifies("REQ_MULTI_ROUND_TOOL_EXECUTION[revision==1]")
def test_tool_round_limit_stops_right_after_round_n(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = "neutral-auth-value"
    monkeypatch.setenv("OPENROUTER_API_KEY_1", value)
    path = openai_chat_path()
    limit = 2
    responses = [
        ScriptedResponse(
            status_code=200,
            headers={"Content-Type": "application/json"},
            body=openai_tool_call_response(
                tool_name="add",
                args={"a": 2, "b": 3},
            ),
        )
        for _ in range(5)
    ]
    router = LLMRouter(
        RouterProfile(
            provider=Provider.OPENROUTER,
            model=Model.DEEPSEEK_V3,
        ),
        temperature=0.0,
        seed=42,
    )
    with ScriptedHTTPServer(port=0, routes={("POST", path): responses}) as server:
        with patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ):
            response = router.query(
                "Keep calling tools.",
                tools=[add],
                max_tool_rounds=limit,
            )
        request_count = server.request_count("POST", path)
        server.retain_current_boundary_evidence()

    assert request_count == limit
    assert response.output_text == ""
    assert len(response.tool_trace) == limit
    assert len(response.tool_calls) == 1
    tool_call = next(iter(response.tool_calls))
    assert tool_call.name == "add"
    assert tool_call.args == {"a": 2, "b": 3}

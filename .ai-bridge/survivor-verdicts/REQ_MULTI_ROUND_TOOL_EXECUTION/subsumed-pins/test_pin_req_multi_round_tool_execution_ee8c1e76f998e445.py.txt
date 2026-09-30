# mutation-pin: REQ_MULTI_ROUND_TOOL_EXECUTION ee8c1e76f998e445
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


def add(*, a: int, b: int) -> dict[str, int]:
    """Return a+b as JSON."""
    return {"result": a + b}


def multiply(*, a: int, b: int) -> dict[str, int]:
    """Return a*b as JSON."""
    return {"result": a * b}


@pytest.mark.verifies("REQ_MULTI_ROUND_TOOL_EXECUTION[revision==1]")
def test_tool_round_limit_produces_response_with_full_trace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_name = "OPENROUTER_API_KEY_1"
    value = "route-credential"
    monkeypatch.setenv(env_name, value)

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
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=openai_tool_call_response(
                    tool_name="multiply",
                    args={"a": 5, "b": 4},
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

    with (
        ScriptedHTTPServer(port=0, routes=routes) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ),
    ):
        response = router.query(
            "Execute the calculation workflow.",
            tools=[add, multiply],
            tool_choice="required",
            max_tool_rounds=2,
        )

    assert response.output_text == ""
    assert len(response.tool_calls) == 1
    assert len(response.tool_trace) == 2
    first_step, second_step = response.tool_trace
    assert first_step.tool_name == "add"
    assert second_step.tool_name == "multiply"

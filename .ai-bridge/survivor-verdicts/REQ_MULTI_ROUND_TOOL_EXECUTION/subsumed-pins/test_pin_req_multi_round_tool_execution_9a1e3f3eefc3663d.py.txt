# mutation-pin: REQ_MULTI_ROUND_TOOL_EXECUTION 9a1e3f3eefc3663d
# pinned-by: claude-opus-5-5
from __future__ import annotations

import json

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


def _body_with_text(tool_name: str, args: dict[str, object], text: str) -> bytes:
    payload = json.loads(openai_tool_call_response(tool_name=tool_name, args=args))
    payload["choices"][0]["message"]["content"] = text
    return json.dumps(payload).encode("utf-8")


@pytest.mark.verifies("REQ_MULTI_ROUND_TOOL_EXECUTION[revision==1]")
def test_tool_round_limit_clears_non_empty_provider_text(
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
                body=_body_with_text(
                    "add", {"a": 7, "b": 6}, "Calling add for you now."
                ),
            ),
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=_body_with_text(
                    "multiply", {"a": 13, "b": 3}, "Now calling multiply."
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
        seed=7,
    )

    with (
        ScriptedHTTPServer(port=0, routes=routes) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ),
    ):
        response = router.query(
            "Compute the two-step arithmetic workflow.",
            tools=[add, multiply],
            tool_choice="required",
            max_tool_rounds=2,
        )

    assert response.output_text == ""
    assert len(response.tool_calls) == 1
    assert next(iter(response.tool_calls)).name == "multiply"
    assert len(response.tool_trace) == 2
    first_step, second_step = response.tool_trace
    assert first_step.tool_name == "add"
    assert second_step.tool_name == "multiply"

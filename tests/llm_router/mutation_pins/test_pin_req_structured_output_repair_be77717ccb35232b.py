# mutation-pin: REQ_STRUCTURED_OUTPUT_REPAIR be77717ccb35232b
# pinned-by: claude-opus-5-5 and claude-opus-5-5 at xhigh, asked again
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import json

import pytest
from pydantic import BaseModel

from llm_router import (
    LLMRouter,
    Model,
    Provider,
    RouterProfile,
    get_config,
    install_config,
)
from tests.llm_router.support.fault_server import (
    ScriptedHTTPServer,
    ScriptedResponse,
)
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
)
from tests.llm_router.support.workers.worker_patches import (
    install_fast_worker_runtime_config,
    patched_openai_sdk,
)

pytestmark = pytest.mark.verification_kind("unit")


class Sum(BaseModel):
    total: int


def add(*, a: int, b: int) -> dict[str, int]:
    """Return a+b as JSON."""
    return {"result": a + b}


def _tool_call_body() -> bytes:
    call = {
        "id": "call_1",
        "type": "function",
        "function": {"name": "add", "arguments": json.dumps({"a": 7, "b": 6})},
    }
    message = {"role": "assistant", "content": "", "tool_calls": [call]}
    return json.dumps(
        {
            "id": "chatcmpl-local-tool",
            "object": "chat.completion",
            "created": 0,
            "model": "local-model",
            "choices": [
                {"index": 0, "message": message, "finish_reason": "tool_calls"}
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }
    ).encode("utf-8")


def _ok(body: bytes) -> ScriptedResponse:
    return ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=body,
    )


@pytest.mark.verifies("REQ_STRUCTURED_OUTPUT_REPAIR[revision==2]")
def test_repair_success_keeps_tool_trace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "route-credential")
    routes = {
        ("POST", openai_chat_path()): [
            _ok(_tool_call_body()),
            _ok(openai_success_response(text="not json at all")),
            _ok(openai_success_response(text='{"total": 13}')),
        ]
    }
    router = LLMRouter(
        RouterProfile(provider=Provider.OPENROUTER, model=Model.DEEPSEEK_V3),
        temperature=0.0,
        seed=7,
    )
    original_config = get_config()
    install_fast_worker_runtime_config(structured_output_max_attempts=2)
    try:
        with (
            ScriptedHTTPServer(port=0, routes=routes) as server,
            patched_openai_sdk(
                forced_base_url=f"{server.base_url}/v1",
                disable_sdk_retries=True,
            ),
        ):
            response = router.query(
                "Add 7 and 6.",
                tools=[add],
                response_schema=Sum,
            )
    finally:
        install_config(original_config)

    assert response.data["parsed"] == {"total": 13}
    assert len(response.tool_trace) == 1
    assert next(iter(response.tool_trace)).tool_name == "add"

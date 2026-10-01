# mutation-pin: REQ_STRUCTURED_OUTPUT_REPAIR FN-7AC89673
# pinned-by: delegate, one pin for 3 pins of _advance_structured_result
# kills: 63b7393727f5c29f SM-12FA1E31 be77717ccb35232b
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


class Empty(BaseModel):
    def __bool__(self) -> bool:
        return False


def add(*, a: int, b: int) -> dict[str, int]:
    """Return a+b as JSON."""
    return {"result": a + b}


def tool_call_body() -> bytes:
    call = {
        "id": "call_1",
        "type": "function",
        "function": {
            "name": "add",
            "arguments": json.dumps({"a": 7, "b": 6}),
        },
    }
    message = {"role": "assistant", "content": "", "tool_calls": [call]}
    return json.dumps(
        {
            "id": "chatcmpl-local-tool",
            "object": "chat.completion",
            "created": 0,
            "model": "local-model",
            "choices": [
                {
                    "index": 0,
                    "message": message,
                    "finish_reason": "tool_calls",
                }
            ],
            "usage": {
                "prompt_tokens": 1,
                "completion_tokens": 1,
                "total_tokens": 2,
            },
        }
    ).encode("utf-8")


def ok_response(body: bytes) -> ScriptedResponse:
    return ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=body,
    )


@pytest.mark.verifies("REQ_STRUCTURED_OUTPUT_REPAIR[revision==2]")
def test_structured_output_repair_success_and_trace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_var = "OPENROUTER_API_KEY_1"
    credential_value = "route-credential"
    monkeypatch.setenv(env_var, credential_value)
    chat_path = openai_chat_path()
    routes = {
        ("POST", chat_path): [
            ok_response(tool_call_body()),
            ok_response(openai_success_response(text="not json at all")),
            ok_response(openai_success_response(text="{}")),
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
                response_schema=Empty,
            )
            records = server.recorded_requests("POST", chat_path)
    finally:
        install_config(original_config)

    assert response.data["parsed"] == {}
    assert len(response.tool_trace) == 1
    assert next(iter(response.tool_trace)).tool_name == "add"

    assert len(records) == 3
    first_req, second_req, repair_req = records
    first_body = first_req.body.decode()
    second_body = second_req.body.decode()
    repair_body = repair_req.body.decode()
    assert "Add 7 and 6." in first_body
    assert "call_1" in second_body
    assert "not json at all" in repair_body
    assert '"json_schema":{"name":"Empty"' in repair_body

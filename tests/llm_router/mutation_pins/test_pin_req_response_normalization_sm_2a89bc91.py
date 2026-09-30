# mutation-pin: REQ_RESPONSE_NORMALIZATION SM-2A89BC91
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import dataclasses
import json

import pytest

import llm_router
from tests.llm_router.support.fault_server import (
    ScriptedHTTPServer,
    ScriptedResponse,
)
from tests.llm_router.support.workers.retry import openai_chat_path

pytestmark = pytest.mark.verification_kind("unit")


def add(*, a: int, b: int) -> dict[str, int]:
    """Return a+b as JSON."""
    return {"result": a + b}


def _tool_call_body(text: str) -> bytes:
    payload = {
        "id": "chatcmpl-local",
        "object": "chat.completion",
        "created": 0,
        "model": "local-model",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": text,
                    "tool_calls": [
                        {
                            "id": "call-1",
                            "type": "function",
                            "function": {
                                "name": "add",
                                "arguments": json.dumps({"a": 7, "b": 6}),
                            },
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
        "usage": {"prompt_tokens": 12, "completion_tokens": 5, "total_tokens": 17},
    }
    return json.dumps(payload).encode("utf-8")


@pytest.mark.verifies("REQ_RESPONSE_NORMALIZATION[revision==1]")
def test_tool_round_limit_public_text_is_normalized_not_raw_provider_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "route-credential")
    routes = {
        ("POST", openai_chat_path()): [
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=_tool_call_body("Calling add for you now."),
            ),
        ]
    }
    original = llm_router.get_config()
    with ScriptedHTTPServer(port=0, routes=routes) as server:
        urls = dict(original.provider_base_urls)
        urls[llm_router.Provider.OPENROUTER] = f"{server.base_url}/v1"
        catalog = dataclasses.replace(original.catalog, provider_base_urls=urls)
        llm_router.install_config(dataclasses.replace(original, catalog=catalog))
        try:
            router = llm_router.LLMRouter(
                llm_router.RouterProfile(
                    provider=llm_router.Provider.OPENROUTER,
                    model=llm_router.Model.DEEPSEEK_V3,
                ),
                temperature=0.0,
                seed=7,
            )
            response = router.query(
                "Add the numbers.",
                tools=[add],
                tool_choice="required",
                max_tool_rounds=1,
            )
        finally:
            llm_router.install_config(original)
    assert response.output_text == ""
    assert next(iter(response.tool_calls)).name == "add"

# mutation-pin: REQ_RESPONSE_NORMALIZATION SM-B9EE9F1F
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import json
from dataclasses import replace

import pytest

import llm_router
from llm_router import LLMRouter, Model, Provider, RouterProfile
from tests.llm_router.support.fault_server import (
    ScriptedHTTPServer,
    ScriptedResponse,
)
from tests.llm_router.support.workers.retry import openai_chat_path

pytestmark = pytest.mark.verification_kind("unit")


def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


def _tool_call_body() -> bytes:
    payload = {
        "id": "chatcmpl-local-tool",
        "object": "chat.completion",
        "created": 0,
        "model": "local-model",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Calling add for you now.",
                    "tool_calls": [
                        {
                            "id": "call_local_tool",
                            "type": "function",
                            "function": {
                                "name": "add",
                                "arguments": json.dumps({"a": 2, "b": 3}),
                            },
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
        "usage": {"prompt_tokens": 12, "completion_tokens": 4, "total_tokens": 16},
    }
    return json.dumps(payload).encode("utf-8")


@pytest.fixture
def original_config():
    original = llm_router.get_config()
    yield original
    llm_router.install_config(original)


@pytest.mark.verifies("REQ_RESPONSE_NORMALIZATION[revision==1]")
def test_round_limit_reply_clears_provider_text_but_keeps_tool_call(
    monkeypatch: pytest.MonkeyPatch,
    original_config: llm_router.LLMRouterConfig,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "neutral-auth-value")
    path = openai_chat_path()
    responses = [
        ScriptedResponse(
            status_code=200,
            headers={"Content-Type": "application/json"},
            body=_tool_call_body(),
        )
        for _ in range(3)
    ]
    with ScriptedHTTPServer(port=0, routes={("POST", path): responses}) as server:
        urls = dict(original_config.provider_base_urls)
        urls[Provider.OPENROUTER] = f"{server.base_url}/v1"
        catalog = replace(original_config.catalog, provider_base_urls=urls)
        llm_router.install_config(replace(original_config, catalog=catalog))
        router = LLMRouter(
            RouterProfile(provider=Provider.OPENROUTER, model=Model.DEEPSEEK_V3),
            temperature=0.0,
            seed=42,
        )
        response = router.query("Keep calling tools.", tools=[add], max_tool_rounds=1)

    assert response.output_text == ""
    assert len(response.tool_calls) == 1
    tool_call = next(iter(response.tool_calls))
    assert tool_call.name == "add"
    assert tool_call.args == {"a": 2, "b": 3}
    assert response.usage is not None
    assert response.usage.total_tokens == 16

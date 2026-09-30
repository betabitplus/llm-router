# mutation-pin: REQ_RESPONSE_NORMALIZATION SM-7211CDB1
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import dataclasses
import json

import pytest

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
from tests.llm_router.support.workers.retry import openai_chat_path

pytestmark = pytest.mark.verification_kind("unit")


def ping(*, value: int) -> dict[str, int]:
    """Return a deterministic tool result."""
    return {"echo": value}


def _tool_reply_with_text() -> bytes:
    return json.dumps(
        {
            "id": "chatcmpl-local-tool",
            "object": "chat.completion",
            "created": 0,
            "model": "local-model",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "raw provider text",
                        "tool_calls": [
                            {
                                "id": "call_local_tool",
                                "type": "function",
                                "function": {
                                    "name": "ping",
                                    "arguments": json.dumps({"value": 7}),
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
            "usage": {
                "prompt_tokens": 12,
                "completion_tokens": 4,
                "total_tokens": 16,
            },
        }
    ).encode("utf-8")


@pytest.mark.verifies("REQ_RESPONSE_NORMALIZATION[revision==1]")
def test_tool_limit_response_has_empty_text_despite_provider_text(
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> None:
    original = get_config()
    request.addfinalizer(lambda: install_config(original))
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "neutral-auth-value")
    path = openai_chat_path()
    responses = [
        ScriptedResponse(
            status_code=200,
            headers={"Content-Type": "application/json"},
            body=_tool_reply_with_text(),
        )
        for _ in range(3)
    ]
    with ScriptedHTTPServer(port=0, routes={("POST", path): responses}) as server:
        catalog = original.catalog
        urls = {
            **catalog.provider_base_urls,
            Provider.OPENROUTER: f"{server.base_url}/v1",
        }
        install_config(
            dataclasses.replace(
                original,
                catalog=dataclasses.replace(catalog, provider_base_urls=urls),
            )
        )
        router = LLMRouter(
            RouterProfile(provider=Provider.OPENROUTER, model=Model.DEEPSEEK_V3),
            temperature=0.0,
            seed=1,
        )
        response = router.query("Keep calling ping.", tools=[ping], max_tool_rounds=1)
        server.retain_current_boundary_evidence()

    assert response.output_text == ""
    assert len(response.tool_calls) == 1
    assert next(iter(response.tool_calls)).name == "ping"
    assert len(response.tool_trace) == 1

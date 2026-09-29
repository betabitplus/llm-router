# mutation-pin: TREQ_QWENCHAT_ADAPTER_BOUNDARY 7b8bea28d9ae00fa
# pinned-by: claude-opus-5-5
from __future__ import annotations

import json
import typing
from dataclasses import dataclass

import pytest

from llm_router._api.types import Model, Provider
from llm_router._internal.capabilities.content import normalize_content
from llm_router._internal.providers.base import (
    ProviderCredential,
    ProviderRequest,
)
from llm_router._internal.providers.qwenchat import (
    QwenChatAdapter,
    json_headers,
)

pytestmark = pytest.mark.verification_kind("unit")

_CAPTURED: dict[str, typing.Any] = {}


@dataclass
class _FakeResponse:
    status_code: int
    text: str


class _FakeAsyncClient:
    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        del args, kwargs

    async def __aenter__(self) -> _FakeAsyncClient:
        return self

    async def __aexit__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        del args, kwargs

    async def post(
        self,
        *args: typing.Any,
        **kwargs: typing.Any,
    ) -> _FakeResponse:
        _CAPTURED["args"] = args
        _CAPTURED["kwargs"] = kwargs
        data = {
            "id": "chatcmpl-1",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "ok"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
            },
        }
        return _FakeResponse(200, json.dumps(data))


@pytest.mark.asyncio
@pytest.mark.verifies("TREQ_QWENCHAT_ADAPTER_BOUNDARY[revision==1]")
async def test_qwenchat_aexecute_chat_post_carries_json_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "llm_router._internal.providers.qwenchat.httpx.AsyncClient",
        _FakeAsyncClient,
    )
    _CAPTURED.clear()
    credential = ProviderCredential(
        key_id=1,
        env_var="ENV_VAR",
        value="neutral_val",
    )
    request = ProviderRequest(
        request_id="req-1",
        provider=Provider.QWENCHAT,
        model=Model.QWEN_MAX_LATEST,
        provider_model="qwen-max",
        credential=credential,
        messages=[normalize_content("test message")],
    )
    adapter = QwenChatAdapter(base_url="http://127.0.0.1:1/api")

    result = await adapter.aexecute(request)

    assert result.output_text == "ok"
    expected = json_headers(request)
    assert expected
    assert _CAPTURED["kwargs"].get("headers") == expected

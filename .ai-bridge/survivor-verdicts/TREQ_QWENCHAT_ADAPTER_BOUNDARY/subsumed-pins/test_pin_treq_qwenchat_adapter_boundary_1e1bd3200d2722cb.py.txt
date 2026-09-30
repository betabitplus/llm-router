# mutation-pin: TREQ_QWENCHAT_ADAPTER_BOUNDARY 1e1bd3200d2722cb
# pinned-by: claude-opus-5-5
from __future__ import annotations

import json
import typing
from dataclasses import dataclass

import pytest

from llm_router._api.errors import ProviderError
from llm_router._api.types import Model, Provider
from llm_router._internal.capabilities.content import normalize_content
from llm_router._internal.providers.base import (
    ProviderCredential,
    ProviderRequest,
    ProviderResult,
)
from llm_router._internal.providers.qwenchat import QwenChatAdapter

pytestmark = pytest.mark.verification_kind("unit")


@dataclass
class _FakeResponse:
    status_code: int
    text: str


class _FakeAsyncClient:
    response: _FakeResponse = _FakeResponse(200, "{}")

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
        del args, kwargs
        return self.response


@pytest.mark.asyncio
@pytest.mark.verifies("TREQ_QWENCHAT_ADAPTER_BOUNDARY[revision==1]")
async def test_qwenchat_aexecute_result_and_provider_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "llm_router._internal.providers.qwenchat.httpx.AsyncClient",
        _FakeAsyncClient,
    )

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

    success_data = {
        "id": "chatcmpl-1",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "proxy response text",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
        },
    }
    _FakeAsyncClient.response = _FakeResponse(
        status_code=200,
        text=json.dumps(success_data),
    )

    result = await adapter.aexecute(request)

    assert isinstance(result, ProviderResult)
    assert result.output_text == "proxy response text"
    assert result.provider == Provider.QWENCHAT
    assert result.model == Model.QWEN_MAX_LATEST

    error_data = {
        "error": {
            "message": "server error",
            "type": "server_error",
            "code": "500",
        },
        "message": "server error",
    }
    _FakeAsyncClient.response = _FakeResponse(
        status_code=500,
        text=json.dumps(error_data),
    )

    with pytest.raises(ProviderError, match=r"status code 500") as exc_info:
        await adapter.aexecute(request)

    assert exc_info.value.provider == Provider.QWENCHAT
    assert exc_info.value.model == Model.QWEN_MAX_LATEST

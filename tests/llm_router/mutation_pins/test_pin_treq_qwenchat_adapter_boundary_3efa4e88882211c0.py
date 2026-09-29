# mutation-pin: TREQ_QWENCHAT_ADAPTER_BOUNDARY 3efa4e88882211c0
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
    ProviderResult,
)
from llm_router._internal.providers.qwenchat import QwenChatAdapter

pytestmark = pytest.mark.verification_kind("unit")


@dataclass
class _FakeResponse:
    status_code: int
    text: str


@pytest.mark.asyncio
@pytest.mark.verifies("TREQ_QWENCHAT_ADAPTER_BOUNDARY[revision==1]")
async def test_qwenchat_aexecute_posts_built_payload_as_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[dict[str, typing.Any]] = []
    success_data = {
        "id": "chatcmpl-boundary-1",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "proxy response text"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 7, "completion_tokens": 3, "total_tokens": 10},
    }
    response = _FakeResponse(status_code=200, text=json.dumps(success_data))

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
            del args
            captured.append(kwargs)
            return response

    monkeypatch.setattr(
        "llm_router._internal.providers.qwenchat.httpx.AsyncClient",
        _FakeAsyncClient,
    )

    credential = ProviderCredential(
        key_id=1,
        env_var="ENV_VAR",
        value="neutral_value",
    )
    request = ProviderRequest(
        request_id="req-boundary-1",
        provider=Provider.QWENCHAT,
        model=Model.QWEN_MAX_LATEST,
        provider_model="qwen-max",
        credential=credential,
        messages=[normalize_content("hello proxy world")],
    )
    adapter = QwenChatAdapter(base_url="http://127.0.0.1:1/api")
    expected_payload = adapter.build_payload(request)

    result = await adapter.aexecute(request)

    assert isinstance(result, ProviderResult)
    assert result.output_text == "proxy response text"
    assert len(captured) == 1
    assert "json" in captured[0]
    assert captured[0]["json"] == expected_payload
    assert captured[0]["json"]["model"] == "qwen-max"

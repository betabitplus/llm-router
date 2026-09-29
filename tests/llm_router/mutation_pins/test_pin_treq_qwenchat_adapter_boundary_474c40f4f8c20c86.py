# mutation-pin: TREQ_QWENCHAT_ADAPTER_BOUNDARY 474c40f4f8c20c86
# pinned-by: claude-opus-5-5
from __future__ import annotations

import typing

import pytest

from llm_router._api.errors import ProviderError
from llm_router._api.types import Model, Provider
from llm_router._internal.capabilities.content import normalize_content
from llm_router._internal.providers.base import (
    ProviderCredential,
    ProviderRequest,
)
from llm_router._internal.providers.qwenchat import QwenChatAdapter

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.asyncio
@pytest.mark.verifies("TREQ_QWENCHAT_ADAPTER_BOUNDARY[revision==1]")
async def test_qwenchat_aexecute_passes_timeout_to_async_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, typing.Any] = {}

    class FakeClient:
        def __init__(self, **kwargs: typing.Any) -> None:
            captured.update(kwargs)

        async def __aenter__(self) -> FakeClient:
            return self

        async def __aexit__(self, *exc_info: typing.Any) -> None:
            return None

        async def post(self, *args: typing.Any, **kwargs: typing.Any) -> None:
            del args, kwargs
            raise ConnectionError("boom")

    monkeypatch.setattr(
        "llm_router._internal.providers.qwenchat.httpx.AsyncClient",
        FakeClient,
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
        messages=[normalize_content("hello")],
    )
    adapter = QwenChatAdapter(
        base_url="http://127.0.0.1:1/api",
        timeout_seconds=7.5,
    )

    with pytest.raises(ProviderError, match=r".+"):
        await adapter.aexecute(request)

    assert captured.get("timeout") == 7.5

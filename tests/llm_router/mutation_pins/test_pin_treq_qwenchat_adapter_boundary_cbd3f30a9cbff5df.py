# mutation-pin: TREQ_QWENCHAT_ADAPTER_BOUNDARY cbd3f30a9cbff5df
# pinned-by: claude-opus-5-5
from __future__ import annotations

import typing

import pytest

from llm_router._api.errors import ProviderError
from llm_router._api.types import Model, Provider
from llm_router._internal.capabilities.content import normalize_content
from llm_router._internal.providers.base import ProviderCredential, ProviderRequest
from llm_router._internal.providers.qwenchat import QwenChatAdapter

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.asyncio
@pytest.mark.verifies("TREQ_QWENCHAT_ADAPTER_BOUNDARY[revision==1]")
async def test_qwenchat_aexecute_transport_error_raises_provider_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cause = ConnectionError("connection failed")

    async def fake_upload_media_async(**kwargs: typing.Any) -> typing.Any:
        del kwargs
        raise cause

    monkeypatch.setattr(
        "llm_router._internal.providers.qwenchat.upload_media_async",
        fake_upload_media_async,
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

    async def fake_abuild_payload(
        request: ProviderRequest,
        *,
        uploader: typing.Any = None,
    ) -> dict[str, typing.Any]:
        del request
        assert uploader is not None
        await uploader("neutral_media")
        return {}

    monkeypatch.setattr(adapter, "abuild_payload", fake_abuild_payload)

    with pytest.raises(ProviderError, match=r".+") as exc_info:
        await adapter.aexecute(request)

    assert exc_info.value.__cause__ is cause
    assert exc_info.value.provider == Provider.QWENCHAT
    assert exc_info.value.model == Model.QWEN_MAX_LATEST

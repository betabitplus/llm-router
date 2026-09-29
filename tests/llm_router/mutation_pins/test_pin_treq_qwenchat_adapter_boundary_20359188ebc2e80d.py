# mutation-pin: TREQ_QWENCHAT_ADAPTER_BOUNDARY 20359188ebc2e80d
# pinned-by: claude-opus-5-5
from __future__ import annotations

import typing

import pytest

from llm_router._api.errors import ProviderError
from llm_router._api.types import Model, Provider
from llm_router._internal.capabilities.content import normalize_content
from llm_router._internal.providers.base import ProviderCredential, ProviderRequest
from llm_router._internal.providers.qwenchat import QwenChatAdapter, transport_failure

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.asyncio
@pytest.mark.verifies("TREQ_QWENCHAT_ADAPTER_BOUNDARY[revision==1]")
async def test_qwenchat_aexecute_provider_error_message_matches_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cause = ConnectionError("network unreachable during media upload")

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
        request_id="req-message-1",
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

    failure = transport_failure(request=request, exc=cause)
    expected = ProviderError(
        failure,
        request.provider,
        request.model,
        message=failure.message,
    )

    with pytest.raises(ProviderError, match=r".+") as exc_info:
        await adapter.aexecute(request)

    assert exc_info.value.__cause__ is cause
    assert str(exc_info.value) == str(expected)

# mutation-pin: TREQ_QWENCHAT_ADAPTER_BOUNDARY 8920c14adbe7aa36
# pinned-by: claude-opus-5-5
from __future__ import annotations

import typing

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


@pytest.mark.asyncio
@pytest.mark.verifies("TREQ_QWENCHAT_ADAPTER_BOUNDARY[revision==1]")
async def test_qwenchat_aexecute_trust_env_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResponse:
        status_code = 200
        text = "{}"

    class FakeAsyncClient:
        def __init__(self, **kwargs: typing.Any) -> None:
            self.trust_env = bool(kwargs.get("trust_env", True))

        async def __aenter__(self) -> FakeAsyncClient:
            return self

        async def __aexit__(
            self,
            exc_type: typing.Any,
            exc_val: typing.Any,
            exc_tb: typing.Any,
        ) -> None:
            del exc_type, exc_val, exc_tb

        async def post(
            self,
            url: str,
            headers: typing.Any = None,
            json: typing.Any = None,
        ) -> FakeResponse:
            del url, headers, json
            if self.trust_env:
                raise OSError("unreachable proxy")
            return FakeResponse()

    async def fake_upload_media_async(**kwargs: typing.Any) -> str:
        client = kwargs["client"]
        if getattr(client, "trust_env", False):
            raise OSError("unreachable proxy")
        return "neutral_media_ref"

    expected_result = ProviderResult(
        data={"result": "ok"},
        provider=Provider.QWENCHAT,
        model=Model.QWEN_MAX_LATEST,
        provider_model="qwen-max",
        output_text="neutral_text",
    )

    def fake_parse_qwenchat_response(
        *,
        request: ProviderRequest,
        status_code: int,
        text: str,
    ) -> ProviderResult:
        del request, status_code, text
        return expected_result

    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:1")
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:1")
    monkeypatch.setenv("ALL_PROXY", "http://127.0.0.1:1")

    monkeypatch.setattr(
        "llm_router._internal.providers.qwenchat.httpx.AsyncClient",
        FakeAsyncClient,
    )
    monkeypatch.setattr(
        "llm_router._internal.providers.qwenchat.upload_media_async",
        fake_upload_media_async,
    )
    monkeypatch.setattr(
        "llm_router._internal.providers.qwenchat.parse_qwenchat_response",
        fake_parse_qwenchat_response,
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

    result = await adapter.aexecute(request)

    assert result is expected_result
    assert result.provider == Provider.QWENCHAT
    assert result.model == Model.QWEN_MAX_LATEST
    assert result.output_text == "neutral_text"

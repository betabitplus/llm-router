from __future__ import annotations

from types import SimpleNamespace

import pytest

from llm_router import Model, Provider, ProviderError
from llm_router._internal.capabilities.content import normalize_content
from llm_router._internal.providers.base import ProviderCredential, ProviderRequest
from llm_router._internal.providers.google_genai import GoogleGenAIAdapter


class FakeAPIError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code


class FakeModels:
    def __init__(self, outcomes: list[object]) -> None:
        self.outcomes = outcomes
        self.calls: list[dict[str, object]] = []

    def generate_content(
        self,
        *,
        model: str,
        contents: object,
        config: object,
    ) -> object:
        self.calls.append({"model": model, "contents": contents, "config": config})
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class FakeAsyncModels(FakeModels):
    async def generate_content(
        self,
        *,
        model: str,
        contents: object,
        config: object,
    ) -> object:
        return super().generate_content(model=model, contents=contents, config=config)


class FakeClient:
    def __init__(self, outcomes: list[object]) -> None:
        self.models = FakeModels(outcomes)
        self.aio = SimpleNamespace(models=FakeAsyncModels(list(outcomes)))


def _response(text: str) -> SimpleNamespace:
    return SimpleNamespace(
        text=text,
        usage_metadata=SimpleNamespace(
            prompt_token_count=2,
            candidates_token_count=3,
            total_token_count=5,
        ),
    )


def _request() -> ProviderRequest:
    return ProviderRequest(
        request_id="req-1",
        provider=Provider.GOOGLE,
        model=Model.GEMINI_FLASH,
        provider_model="gemini-3.6-flash",
        credential=ProviderCredential(
            key_id=1,
            env_var="GOOGLE_API_KEY_1",
            value="secret",
        ),
        messages=[normalize_content("hello")],
        temperature=0.0,
        seed=7,
    )


def test_sync_google_adapter_uses_sdk_boundary_and_normalizes_result() -> None:
    client = FakeClient([_response("ok")])

    result = GoogleGenAIAdapter(client=client).execute(_request())

    assert result.output_text == "ok"
    assert result.usage.total_tokens == 5
    assert client.models.calls[0]["model"] == "gemini-3.6-flash"
    config = client.models.calls[0]["config"]
    assert config.temperature == 0.0
    assert config.seed == 7


@pytest.mark.asyncio
async def test_async_google_adapter_uses_sdk_async_boundary() -> None:
    client = FakeClient([_response("async ok")])

    result = await GoogleGenAIAdapter(client=client).aexecute(_request())

    assert result.output_text == "async ok"
    assert client.aio.models.calls[0]["model"] == "gemini-3.6-flash"


def test_google_sdk_retryable_status_is_translated_to_provider_error() -> None:
    client = FakeClient([FakeAPIError(503, "provider said no")])

    with pytest.raises(ProviderError) as exc_info:
        GoogleGenAIAdapter(client=client).execute(_request())

    assert exc_info.value.cause.status_code == 503
    assert exc_info.value.cause.retryable is True
    assert exc_info.value.cause.retry_reason == "retryable_status"

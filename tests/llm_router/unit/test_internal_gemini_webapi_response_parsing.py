from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from llm_router import Model, Provider, ProviderError, UsageStats
from llm_router._internal.capabilities.content import normalize_content
from llm_router._internal.capabilities.schema import normalize_schema
from llm_router._internal.capabilities.tools import ToolRegistry
from llm_router._internal.providers.base import ProviderCredential, ProviderRequest
from llm_router._internal.providers.gemini_webapi import (
    GeminiWebAPIAdapter,
    parse_gemini_webapi_response,
)


class Reply(BaseModel):
    answer: str


class FakeStatusError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code


class FakeProviderCodeError(Exception):
    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code


class FakeTextStatusError(Exception):
    pass


class FakeClient:
    def __init__(self, outcome: object) -> None:
        self.outcome = outcome

    async def generate_content(self, prompt: str, **kwargs: object) -> object:
        _ = prompt
        _ = kwargs
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


def add(a: int, b: int) -> dict[str, int]:
    return {"result": a + b}


def _request(**overrides: object) -> ProviderRequest:
    values = {
        "request_id": "req-1",
        "provider": Provider.GEMINI_WEBAPI,
        "model": Model.GEMINI_FLASH,
        "provider_model": "gemini-3.0-flash",
        "credential": ProviderCredential(
            key_id=1,
            env_var="GEMINI_WEBAPI_COOKIE",
            value="",
        ),
        "messages": [normalize_content("hello")],
    }
    values.update(overrides)
    return ProviderRequest(**values)


def _usage() -> SimpleNamespace:
    return SimpleNamespace(
        prompt_tokens=2,
        completion_tokens=3,
        total_tokens=5,
    )


def test_parse_text_and_usage() -> None:
    response = SimpleNamespace(text=" ok ", usage=_usage())

    result = parse_gemini_webapi_response(request=_request(), response=response)

    assert result.output_text == "ok"
    assert result.usage == UsageStats(input_tokens=2, output_tokens=3, total_tokens=5)
    assert result.data["text"] == "ok"


def test_parse_structured_output_from_prompted_text() -> None:
    request = _request(schema=normalize_schema(Reply))
    response = SimpleNamespace(text='prefix {"answer": "ok"} suffix')

    result = parse_gemini_webapi_response(request=request, response=response)

    assert result.data["parsed"] == {"answer": "ok"}


def test_parse_textual_tool_call() -> None:
    request = _request(tool_registry=ToolRegistry.from_tools([add]))
    response = SimpleNamespace(text="add(20, 22)")

    result = parse_gemini_webapi_response(request=request, response=response)

    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "add"
    assert result.tool_calls[0].args == {"a": 20, "b": 22}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("outcome", "retryable", "retry_reason", "status_code"),
    [
        (FakeStatusError(503, "try again"), True, "retryable_status", 503),
        (FakeStatusError(400, "bad request"), False, "caller_or_auth_status", 400),
        (
            FakeTextStatusError("Failed to generate contents. Status: 500"),
            True,
            "retryable_status",
            500,
        ),
        (
            FakeProviderCodeError(1060, "server refused"),
            False,
            "gemini_webapi_error_code",
            1060,
        ),
    ],
)
async def test_sdk_errors_are_classified(
    outcome: Exception,
    retryable: bool,
    retry_reason: str,
    status_code: int,
) -> None:
    adapter = GeminiWebAPIAdapter(client=FakeClient(outcome))

    with pytest.raises(ProviderError) as exc_info:
        await adapter.aexecute(_request())

    assert exc_info.value.cause.status_code == status_code
    assert exc_info.value.cause.retryable is retryable
    assert exc_info.value.cause.retry_reason == retry_reason

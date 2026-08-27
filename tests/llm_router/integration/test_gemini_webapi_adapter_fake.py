from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from llm_router import Model, Provider, ProviderError, VideoSchema
from llm_router._internal.capabilities.content import normalize_content
from llm_router._internal.capabilities.schema import normalize_schema
from llm_router._internal.capabilities.tools import ToolRegistry
from llm_router._internal.providers.base import ProviderCredential, ProviderRequest
from llm_router._internal.providers.gemini_webapi import GeminiWebAPIAdapter


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


class FakeClient:
    def __init__(self, outcomes: list[object]) -> None:
        self.outcomes = outcomes
        self.calls: list[dict[str, object]] = []

    async def generate_content(self, prompt: str, **kwargs: object) -> object:
        files = kwargs.get("files", [])
        self.calls.append(
            {
                "prompt": prompt,
                "model": kwargs.get("model"),
                "file_names": [Path(path).name for path in files],
            }
        )
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


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


def _response(text: str) -> SimpleNamespace:
    return SimpleNamespace(
        text=text,
        usage={"prompt_tokens": 2, "completion_tokens": 3},
    )


def test_sync_gemini_webapi_crosses_sdk_boundary() -> None:
    client = FakeClient([_response("ok")])

    result = GeminiWebAPIAdapter(client=client).execute(_request())

    assert result.output_text == "ok"
    assert result.usage.total_tokens == 5
    assert client.calls[0]["model"] == "gemini-3.0-flash"
    assert client.calls[0]["prompt"] == "hello"


@pytest.mark.asyncio
async def test_async_gemini_webapi_passes_local_video_path(tmp_path: Path) -> None:
    video_path = tmp_path / "clip.mp4"
    video_path.write_bytes(b"video")
    request = _request(
        messages=[normalize_content([VideoSchema(path=str(video_path), fps=1)])]
    )
    client = FakeClient([_response("video ok")])

    result = await GeminiWebAPIAdapter(client=client).aexecute(request)

    assert result.output_text == "video ok"
    assert client.calls[0]["file_names"] == ["clip.mp4"]


def test_gemini_webapi_retryable_status_is_translated() -> None:
    client = FakeClient([FakeStatusError(503, "try again")])

    with pytest.raises(ProviderError) as exc_info:
        GeminiWebAPIAdapter(client=client).execute(_request())

    assert exc_info.value.cause.status_code == 503
    assert exc_info.value.cause.retryable is True
    assert exc_info.value.cause.retry_reason == "retryable_status"


def test_gemini_webapi_provider_specific_error_code_is_preserved() -> None:
    client = FakeClient([FakeProviderCodeError(1060, "server refused")])

    with pytest.raises(ProviderError) as exc_info:
        GeminiWebAPIAdapter(client=client).execute(_request())

    assert exc_info.value.cause.status_code == 1060
    assert exc_info.value.cause.retryable is False
    assert exc_info.value.cause.retry_reason == "gemini_webapi_error_code"


def test_gemini_webapi_normalizes_structured_and_textual_tool_outputs() -> None:
    client = FakeClient([_response('{"answer": "ok"}'), _response("add(2, 3)")])
    adapter = GeminiWebAPIAdapter(client=client)
    registry = ToolRegistry.from_tools([add])

    structured = adapter.execute(_request(schema=normalize_schema(Reply)))
    tool = adapter.execute(_request(tool_registry=registry))

    assert structured.data["parsed"] == {"answer": "ok"}
    assert tool.tool_calls[0].name == "add"
    assert tool.tool_calls[0].args == {"a": 2, "b": 3}

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


def test_sync_gemini_webapi_uses_fake_client_and_normalizes_text() -> None:
    client = FakeClient([_response("ok")])

    result = GeminiWebAPIAdapter(client=client).execute(_request())

    assert result.output_text == "ok"
    assert result.usage.total_tokens == 5
    assert client.calls[0]["model"] == "gemini-3.0-flash"
    assert client.calls[0]["prompt"] == "hello"


@pytest.mark.asyncio
async def test_async_gemini_webapi_uploads_local_video_path(tmp_path: Path) -> None:
    video_path = tmp_path / "clip.mp4"
    video_path.write_bytes(b"video")
    request = _request(
        messages=[normalize_content([VideoSchema(path=str(video_path), fps=1)])]
    )
    client = FakeClient([_response("video ok")])

    result = await GeminiWebAPIAdapter(client=client).aexecute(request)

    assert result.output_text == "video ok"
    assert client.calls[0]["file_names"] == ["clip.mp4"]


@pytest.mark.asyncio
async def test_gemini_webapi_reuses_initialized_runtime_client() -> None:
    status_checks = 0
    client_builds = 0
    client_inits = 0
    client = FakeClient([_response("one"), _response("two")])

    def runtime_status() -> dict[str, bool]:
        nonlocal status_checks
        status_checks += 1
        return {"ready": True}

    def build_client() -> FakeClient:
        nonlocal client_builds
        client_builds += 1
        return client

    async def init_client(candidate: object, timeout_seconds: float) -> object:
        nonlocal client_inits
        del timeout_seconds
        client_inits += 1
        return candidate

    adapter = GeminiWebAPIAdapter(
        runtime_status_func=runtime_status,
        client_builder=build_client,
        init_client_func=init_client,
    )

    first = await adapter.aexecute(_request())
    second = await adapter.aexecute(_request())

    assert first.output_text == "one"
    assert second.output_text == "two"
    assert status_checks == 1
    assert client_builds == 1
    assert client_inits == 1
    assert len(client.calls) == 2


@pytest.mark.parametrize(
    ("outcome", "retryable", "retry_reason", "status_code"),
    [
        (FakeStatusError(503, "try again"), True, "retryable_status", 503),
        (FakeStatusError(400, "bad request"), False, "caller_or_auth_status", 400),
        (
            FakeProviderCodeError(1060, "server refused"),
            False,
            "gemini_webapi_error_code",
            1060,
        ),
    ],
)
def test_gemini_webapi_errors_are_classified(
    outcome: Exception,
    retryable: bool,
    retry_reason: str,
    status_code: int,
) -> None:
    client = FakeClient([outcome])

    with pytest.raises(ProviderError) as exc_info:
        GeminiWebAPIAdapter(client=client).execute(_request())

    assert exc_info.value.cause.status_code == status_code
    assert exc_info.value.cause.retryable is retryable
    assert exc_info.value.cause.retry_reason == retry_reason


def test_gemini_webapi_structured_and_textual_tool_outputs_are_normalized() -> None:
    client = FakeClient([_response('{"answer": "ok"}'), _response("add(2, 3)")])
    adapter = GeminiWebAPIAdapter(client=client)
    registry = ToolRegistry.from_tools([add])

    structured = adapter.execute(_request(schema=normalize_schema(Reply)))
    tool = adapter.execute(_request(tool_registry=registry))

    assert structured.data["parsed"] == {"answer": "ok"}
    assert tool.tool_calls[0].name == "add"
    assert tool.tool_calls[0].args == {"a": 2, "b": 3}

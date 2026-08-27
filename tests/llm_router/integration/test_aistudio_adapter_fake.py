from __future__ import annotations

import json

import pytest

from llm_router import Model, Provider, ProviderError, VideoUrlSchema
from llm_router._internal.capabilities.content import normalize_content
from llm_router._internal.providers.aistudio import AIStudioAdapter
from llm_router._internal.providers.base import ProviderCredential, ProviderRequest
from llm_router._internal.providers.openai_compatible import OpenAICompatibleAdapter
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    aistudio_video_path,
    openai_chat_path,
    openai_success_response,
)


def _request(**overrides: object) -> ProviderRequest:
    values = {
        "request_id": "req-1",
        "provider": Provider.AISTUDIO,
        "model": Model.GEMINI_FLASH,
        "provider_model": "gemini-3.6-flash",
        "credential": ProviderCredential(
            key_id=1,
            env_var="AISTUDIO_API_KEY_1",
            value="secret",
        ),
        "messages": [normalize_content("hello")],
    }
    values.update(overrides)
    return ProviderRequest(**values)


def _adapter(server: ScriptedHTTPServer) -> AIStudioAdapter:
    base_url = f"{server.base_url}/v1"
    return AIStudioAdapter(
        base_url=base_url,
        openai_adapter=OpenAICompatibleAdapter(base_url=base_url),
    )


def _native_success_response(*, text: str) -> bytes:
    return (
        "data: "
        + json.dumps(
            {
                "candidates": [{"content": {"parts": [{"text": text}]}}],
                "usageMetadata": {
                    "promptTokenCount": 2,
                    "candidatesTokenCount": 3,
                    "totalTokenCount": 5,
                },
            }
        )
        + "\n\ndata: [DONE]\n\n"
    ).encode("utf-8")


def _native_error_response(*, status_code: int, message: str) -> bytes:
    return json.dumps({"error": {"code": status_code, "message": message}}).encode(
        "utf-8"
    )


def test_aistudio_text_uses_openai_compatible_transport() -> None:
    path = openai_chat_path()
    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", path): [
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=openai_success_response(text="openai ok"),
                )
            ]
        },
    ) as server:
        result = _adapter(server).execute(_request())

        assert result.output_text == "openai ok"
        body = json.loads(server.recorded_requests("POST", path)[0].body)
        assert body["messages"] == [{"role": "user", "content": "hello"}]


def test_aistudio_video_uses_native_transport() -> None:
    path = aistudio_video_path(model=Model.GEMINI_FLASH)
    request = _request(
        messages=[
            normalize_content(
                [VideoUrlSchema(url="https://example.test/clip.mp4", fps=2)]
            )
        ]
    )
    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", path): [
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "text/event-stream"},
                    body=_native_success_response(text='{"action": "jump"}'),
                )
            ]
        },
    ) as server:
        result = _adapter(server).execute(request)

        recorded = server.recorded_requests("POST", path)[0]
        body = json.loads(recorded.body)
        assert result.output_text == '{"action": "jump"}'
        assert result.usage.total_tokens == 5
        assert body["contents"][0]["parts"][0]["fileData"]["fileUri"] == (
            "https://example.test/clip.mp4"
        )
        assert recorded.headers["x-goog-api-key"] == "secret"


def test_aistudio_native_retryable_status_is_translated() -> None:
    path = aistudio_video_path(model=Model.GEMINI_FLASH)
    request = _request(
        messages=[
            normalize_content(
                [VideoUrlSchema(url="https://example.test/clip.mp4", fps=2)]
            )
        ]
    )
    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", path): [
                ScriptedResponse(
                    status_code=503,
                    headers={"Content-Type": "application/json"},
                    body=_native_error_response(
                        status_code=503,
                        message="provider said no",
                    ),
                )
            ]
        },
    ) as server:
        with pytest.raises(ProviderError) as exc_info:
            _adapter(server).execute(request)

        assert exc_info.value.cause.status_code == 503
        assert exc_info.value.cause.retryable is True
        assert exc_info.value.cause.retry_reason == "retryable_status"

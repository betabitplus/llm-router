from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image
from pydantic import BaseModel

from llm_router import FileSchema, Model, Provider, ProviderError
from llm_router._internal.capabilities.content import normalize_content
from llm_router._internal.capabilities.schema import normalize_schema
from llm_router._internal.capabilities.tools import ToolRegistry
from llm_router._internal.providers.base import ProviderCredential, ProviderRequest
from llm_router._internal.providers.qwenchat import QwenChatAdapter
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    qwen_chat_path,
    qwen_error_response,
    qwen_success_response,
    qwen_upload_path,
    qwen_upload_success_response,
    run_retry_worker,
)


class Reply(BaseModel):
    answer: str


def add(a: int, b: int) -> dict[str, int]:
    return {"result": a + b}


def _request(**overrides: object) -> ProviderRequest:
    values = {
        "request_id": "req-1",
        "provider": Provider.QWENCHAT,
        "model": Model.QWEN_MAX_LATEST,
        "provider_model": "qwen-max-latest",
        "credential": ProviderCredential(
            key_id=1,
            env_var="QWENCHAT_API_KEY_1",
            value="secret",
        ),
        "messages": [normalize_content("hello")],
        "temperature": 0.0,
        "seed": 42,
    }
    values.update(overrides)
    return ProviderRequest(**values)


def _adapter(server: ScriptedHTTPServer) -> QwenChatAdapter:
    return QwenChatAdapter(base_url=f"{server.base_url}/api")


pytestmark = [
    pytest.mark.verifies("TREQ_QWENCHAT_ADAPTER_BOUNDARY[revision==1]"),
    pytest.mark.verification_kind("integration"),
]


def test_qwenchat_text_crosses_proxy_http_boundary() -> None:
    path = qwen_chat_path()
    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", path): [
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=qwen_success_response(text="ok"),
                )
            ]
        },
    ) as server:
        result = _adapter(server).execute(_request())

        recorded = server.recorded_requests("POST", path)[0]
        body = json.loads(recorded.body)
        assert result.output_text == "ok"
        assert result.usage.total_tokens == 15
        assert body["messages"] == [{"role": "user", "content": "hello"}]
        assert body["temperature"] == 0.0
        assert body["seed"] == 42
        assert recorded.headers["Authorization"] == "Bearer secret"


def test_qwenchat_uploads_media_before_chat(tmp_path: Path) -> None:
    path = qwen_chat_path()
    upload_path = qwen_upload_path()
    pdf_path = tmp_path / "input.pdf"
    pdf_path.write_bytes(b"%PDF")
    request = _request(
        messages=[
            normalize_content(
                [
                    "look",
                    Image.new("RGB", (10, 10)),
                    FileSchema(path=str(pdf_path), mime_type="application/pdf"),
                    "done",
                ]
            )
        ]
    )
    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", upload_path): [
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=qwen_upload_success_response(url="https://upload.test/1"),
                ),
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=qwen_upload_success_response(url="https://upload.test/2"),
                ),
            ],
            ("POST", path): [
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=qwen_success_response(text="media ok"),
                )
            ],
        },
    ) as server:
        result = _adapter(server).execute(request)

        assert result.output_text == "media ok"
        assert server.request_count("POST", upload_path) == 2
        chat_body = json.loads(server.recorded_requests("POST", path)[0].body)
        assert chat_body["messages"][0]["content"] == [
            {"type": "text", "text": "look"},
            {"type": "image", "image": "https://upload.test/1"},
            {"type": "file", "file": "https://upload.test/2"},
            {"type": "text", "text": "done"},
        ]


def test_qwenchat_retries_upload_before_chat() -> None:
    upload_path = qwen_upload_path()
    chat_path = qwen_chat_path()
    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", upload_path): [
                ScriptedResponse(
                    status_code=429,
                    headers={"Content-Type": "application/json"},
                    body=qwen_error_response(
                        status_code=429, message="retry upload once"
                    ),
                ),
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=qwen_upload_success_response(
                        url="https://local.qwen/uploaded/image.png"
                    ),
                ),
            ],
            ("POST", chat_path): [
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=qwen_success_response(text="upload retry ok"),
                )
            ],
        },
    ) as server:
        result = run_retry_worker(
            case="qwenchat",
            scenario="retryable_upload",
            server_base_url=server.base_url,
        )

        assert result.ok is True, result.error_message
        assert result.output_text == "upload retry ok"
        assert server.request_count("POST", upload_path) == 2
        assert server.request_count("POST", chat_path) == 1


def test_qwenchat_retryable_status_is_translated_to_provider_error() -> None:
    path = qwen_chat_path()
    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", path): [
                ScriptedResponse(
                    status_code=503,
                    headers={"Content-Type": "application/json"},
                    body=qwen_error_response(
                        status_code=503,
                        message="provider said no",
                    ),
                )
            ]
        },
    ) as server:
        with pytest.raises(ProviderError) as exc_info:
            _adapter(server).execute(_request())

        assert exc_info.value.cause.status_code == 503
        assert exc_info.value.cause.retryable is True
        assert exc_info.value.cause.retry_reason == "retryable_status"


def test_qwenchat_normalizes_structured_and_textual_tool_outputs() -> None:
    path = qwen_chat_path()
    registry = ToolRegistry.from_tools([add])
    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", path): [
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=qwen_success_response(text='{"answer": "ok"}'),
                ),
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=qwen_success_response(text="add(a=2, b=3)"),
                ),
            ]
        },
    ) as server:
        adapter = _adapter(server)
        structured = adapter.execute(_request(schema=normalize_schema(Reply)))
        tool = adapter.execute(_request(tool_registry=registry))

        assert structured.data["parsed"] == {"answer": "ok"}
        assert tool.tool_calls[0].name == "add"
        assert tool.tool_calls[0].args == {"a": 2, "b": 3}

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image
from pydantic import BaseModel

from llm_router import FileSchema, Model, Provider, VideoSchema, VideoUrlSchema
from llm_router._internal.capabilities.content import normalize_content
from llm_router._internal.capabilities.schema import normalize_schema
from llm_router._internal.capabilities.tools import (
    ToolRegistry,
    normalize_tool_choice,
)
from llm_router._internal.providers.base import ProviderCredential, ProviderRequest
from llm_router._internal.providers.qwenchat import (
    QwenChatAdapter,
    encode_multipart_single_file,
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
    }
    values.update(overrides)
    return ProviderRequest(**values)


def test_text_payload_uses_proxy_chat_completion_shape() -> None:
    request = _request(temperature=0.2, seed=42, kwargs={"top_p": 0.9})

    payload = QwenChatAdapter(base_url="http://proxy.test/api").build_payload(request)

    assert payload["model"] == "qwen-max-latest"
    assert payload["messages"] == [{"role": "user", "content": "hello"}]
    assert payload["stream"] is False
    assert payload["temperature"] == 0.2
    assert payload["seed"] == 42
    assert payload["top_p"] == 0.9


def test_upload_multipart_is_deterministic() -> None:
    body, content_type = encode_multipart_single_file(
        filename="input.pdf",
        content_type="application/pdf",
        content=b"%PDF",
    )

    assert content_type == "multipart/form-data; boundary=llm-router-qwenchat-upload"
    assert b'name="file"; filename="input.pdf"' in body
    assert b"Content-Type: application/pdf" in body
    assert body.endswith(b"--llm-router-qwenchat-upload--\r\n")


def test_media_payload_uploads_and_preserves_order(tmp_path: Path) -> None:
    pdf_path = tmp_path / "input.pdf"
    pdf_path.write_bytes(b"%PDF")
    video_path = tmp_path / "clip.mp4"
    video_path.write_bytes(b"video")
    image = Image.new("RGB", (10, 10))
    request = _request(
        messages=[
            normalize_content(
                [
                    "first",
                    "second",
                    image,
                    "after image",
                    FileSchema(path=str(pdf_path), mime_type="application/pdf"),
                    VideoSchema(path=str(video_path), fps=1),
                    VideoUrlSchema(url="https://example.test/clip.mp4"),
                ]
            )
        ]
    )
    uploads: list[str] = []

    def uploader(_media: object) -> str:
        uploads.append(type(_media).__name__)
        return f"https://upload.test/{len(uploads)}"

    payload = QwenChatAdapter(base_url="http://proxy.test/api").build_payload(
        request,
        uploader=uploader,
    )

    content = payload["messages"][0]["content"]
    assert uploads == ["ImageMedia", "FileMedia", "VideoFileMedia"]
    assert content == [
        {"type": "text", "text": "first\n\nsecond"},
        {"type": "image", "image": "https://upload.test/1"},
        {"type": "text", "text": "after image"},
        {"type": "file", "file": "https://upload.test/2"},
        {"type": "file", "file": "https://upload.test/3"},
        {"type": "file", "file": "https://example.test/clip.mp4"},
    ]


def test_schema_instruction_is_prepended_to_user_content() -> None:
    request = _request(schema=normalize_schema(Reply))

    payload = QwenChatAdapter(base_url="http://proxy.test/api").build_payload(request)

    content = payload["messages"][0]["content"]
    assert "Output MUST be valid JSON" in content
    assert "Reply" in content
    assert content.endswith("hello")


def test_tools_and_named_choice_translate_to_proxy_payload() -> None:
    registry = ToolRegistry.from_tools([add])
    choice = normalize_tool_choice("add", registry=registry)
    request = _request(tool_registry=registry, tool_choice=choice)

    payload = QwenChatAdapter(base_url="http://proxy.test/api").build_payload(request)

    assert payload["messages"][0]["role"] == "user"
    assert "You can use local tools." in payload["messages"][0]["content"]
    assert "add(a, b)" in payload["messages"][0]["content"]
    assert payload["tools"][0]["function"]["name"] == "add"
    assert "tool_choice" not in payload
    json.dumps(payload)

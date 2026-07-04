from __future__ import annotations

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
from llm_router._internal.providers.google_genai import GoogleGenAIAdapter


class Reply(BaseModel):
    answer: str


def lookup(query: str) -> str:
    """Look up a value."""
    return query


def _request(**overrides: object) -> ProviderRequest:
    values = {
        "request_id": "req-1",
        "provider": Provider.GOOGLE,
        "model": Model.GEMINI_FLASH,
        "provider_model": "gemini-2.5-flash",
        "credential": ProviderCredential(
            key_id=1,
            env_var="GOOGLE_API_KEY_1",
            value="secret",
        ),
        "messages": [normalize_content("hello")],
    }
    values.update(overrides)
    return ProviderRequest(**values)


def test_text_config_and_schema_translate_to_google_native_payload() -> None:
    request = _request(
        temperature=0.2,
        seed=42,
        schema=normalize_schema(Reply),
    )
    adapter = GoogleGenAIAdapter()

    contents = adapter.build_contents(request)
    config = adapter.build_config(request)

    assert contents[0].role == "user"
    assert contents[0].parts[0].text == "hello"
    assert config.temperature == 0.2
    assert config.seed == 42
    assert config.response_mime_type == "application/json"
    assert config.response_schema["title"] == "Reply"
    assert config.response_schema["type"] == "OBJECT"


def test_media_parts_translate_to_google_native_parts(tmp_path: Path) -> None:
    pdf_path = tmp_path / "input.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 local")
    video_path = tmp_path / "clip.mp4"
    video_path.write_bytes(b"video")
    image = Image.new("RGB", (10, 10))
    request = _request(
        messages=[
            normalize_content(
                [
                    image,
                    FileSchema(path=str(pdf_path), mime_type="application/pdf"),
                    VideoSchema(path=str(video_path), fps=2, start_offset=1),
                    VideoUrlSchema(url="https://example.test/clip.mp4", fps=3),
                ]
            )
        ]
    )

    parts = GoogleGenAIAdapter().build_contents(request)[0].parts

    assert parts[0].inline_data.mime_type == "image/png"
    assert parts[1].inline_data.mime_type == "application/pdf"
    assert parts[1].inline_data.data == b"%PDF-1.4 local"
    assert parts[2].inline_data.mime_type == "video/mp4"
    assert parts[2].video_metadata.fps == 2.0
    assert parts[2].video_metadata.start_offset == "1s"
    assert parts[3].file_data.file_uri == "https://example.test/clip.mp4"
    assert parts[3].video_metadata.fps == 3.0


def test_tools_and_named_tool_choice_translate_to_google_config() -> None:
    registry = ToolRegistry.from_tools([lookup])
    choice = normalize_tool_choice("lookup", registry=registry)
    request = _request(tool_registry=registry, tool_choice=choice)

    config = GoogleGenAIAdapter().build_config(request)

    declaration = config.tools[0].function_declarations[0]
    function_config = config.tool_config.function_calling_config
    assert declaration.name == "lookup"
    assert declaration.parameters.required == ["query"]
    assert str(function_config.mode).endswith("ANY")
    assert function_config.allowed_function_names == ["lookup"]

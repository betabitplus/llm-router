from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image
from pydantic import BaseModel

from llm_router import (
    FileSchema,
    Model,
    Provider,
    ProviderError,
    VideoSchema,
    VideoUrlSchema,
)
from llm_router._internal.capabilities.content import normalize_content
from llm_router._internal.capabilities.schema import normalize_schema
from llm_router._internal.capabilities.tools import (
    ToolRegistry,
    normalize_tool_choice,
)
from llm_router._internal.providers.base import ProviderCredential, ProviderRequest
from llm_router._internal.providers.gemini_webapi import GeminiWebAPIAdapter


class Reply(BaseModel):
    answer: str


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


def test_text_and_schema_translate_to_prompt(tmp_path: Path) -> None:
    request = _request(schema=normalize_schema(Reply))

    prompt, files = GeminiWebAPIAdapter(client=object()).build_prompt_and_files(
        request,
        temp_dir=tmp_path,
    )

    assert "Output MUST be valid JSON" in prompt
    assert "Reply" in prompt
    assert "hello" in prompt
    assert "User: hello" not in prompt
    assert files == []


def test_session_transcript_labels_are_not_double_prefixed(tmp_path: Path) -> None:
    request = _request(
        messages=[
            normalize_content(
                [
                    "system",
                    "User: hello",
                    "Assistant: answer",
                    "User: next",
                ]
            )
        ]
    )

    prompt, files = GeminiWebAPIAdapter(client=object()).build_prompt_and_files(
        request,
        temp_dir=tmp_path,
    )

    assert prompt == "system\n\nUser: hello\n\nAssistant: answer\n\nUser: next"
    assert files == []


def test_media_translate_to_sdk_file_paths_and_video_url_prompt(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "input.pdf"
    pdf_path.write_bytes(b"%PDF")
    video_path = tmp_path / "clip.mp4"
    video_path.write_bytes(b"video")
    image = Image.new("RGB", (10, 10))
    request = _request(
        messages=[
            normalize_content(
                [
                    image,
                    FileSchema(path=str(pdf_path), mime_type="application/pdf"),
                    VideoSchema(path=str(video_path), fps=2),
                    VideoUrlSchema(url="https://example.test/clip.mp4"),
                ]
            )
        ]
    )

    prompt, files = GeminiWebAPIAdapter(client=object()).build_prompt_and_files(
        request,
        temp_dir=tmp_path,
    )

    assert "https://example.test/clip.mp4" in prompt
    assert len(files) == 3
    image_digest = files[0].stem.removeprefix("image_")
    assert files[0].suffix == ".png"
    assert len(image_digest) == 16
    int(image_digest, 16)
    assert files[0].read_bytes()
    assert files[1] == pdf_path
    assert files[2] == video_path


def test_tools_and_named_choice_translate_to_textual_prompt(tmp_path: Path) -> None:
    registry = ToolRegistry.from_tools([add])
    choice = normalize_tool_choice("add", registry=registry)
    request = _request(tool_registry=registry, tool_choice=choice)

    prompt, files = GeminiWebAPIAdapter(client=object()).build_prompt_and_files(
        request,
        temp_dir=tmp_path,
    )

    assert "exactly one function call" in prompt
    assert "You MUST use only the tool `add`" in prompt
    assert "add(a, b)" in prompt
    assert files == []


@pytest.mark.asyncio
async def test_preflight_failure_is_safe_provider_error() -> None:
    adapter = GeminiWebAPIAdapter(
        runtime_status_func=lambda: {"ready": False, "reason": "missing cookie"},
        client_builder=object,
    )

    with pytest.raises(ProviderError) as exc_info:
        await adapter.aexecute(_request())

    assert exc_info.value.cause.retryable is False
    assert exc_info.value.cause.retry_reason == "runtime_preflight_failed"
    assert "missing cookie" in str(exc_info.value)

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from llm_router import ChatMessage, FileSchema, VideoSchema, VideoUrlSchema
from llm_router._internal.capabilities.content import (
    MediaPart,
    TextPart,
    normalize_chat_message,
    normalize_content,
)


def test_normalize_content_preserves_text_and_media_order(tmp_path: Path) -> None:
    file_path = tmp_path / "doc.txt"
    file_path.write_text("hello", encoding="utf-8")
    video_path = tmp_path / "clip.mp4"
    video_path.write_bytes(b"video")
    image = Image.new("RGB", (10, 12))

    message = normalize_content(
        [
            "lead",
            FileSchema(path=str(file_path), mime_type="text/plain"),
            image,
            VideoSchema(path=str(video_path), fps=2, start_offset=1),
            VideoUrlSchema(url="https://video.example/clip.mp4", end_offset=5),
            "tail",
        ]
    )

    assert message.role == "user"
    assert [part.kind for part in message.parts] == [
        "text",
        "media",
        "media",
        "media",
        "media",
        "text",
    ]
    assert isinstance(message.parts[0], TextPart)
    assert message.parts[0].text == "lead"
    assert isinstance(message.parts[1], MediaPart)
    assert message.parts[1].media.kind == "file"
    assert isinstance(message.parts[2], MediaPart)
    assert message.parts[2].media.kind == "image"
    assert message.parts[2].media.width == 10
    assert isinstance(message.parts[3], MediaPart)
    assert message.parts[3].media.kind == "video_file"
    assert message.parts[3].media.fps == 2
    assert isinstance(message.parts[4], MediaPart)
    assert message.parts[4].media.kind == "video_url"
    assert isinstance(message.parts[5], TextPart)
    assert message.parts[5].text == "tail"


def test_normalize_string_content_builds_single_text_message() -> None:
    message = normalize_content("hello")

    assert message.role == "user"
    assert message.parts == (TextPart(kind="text", text="hello"),)


def test_normalize_chat_message_copies_metadata() -> None:
    public_message = ChatMessage(
        role="assistant",
        parts=("answer",),
        meta={"provider": "test"},
    )

    normalized = normalize_chat_message(public_message)
    public_message.meta["provider"] = "mutated"

    assert normalized.role == "assistant"
    assert normalized.parts == (TextPart(kind="text", text="answer"),)
    assert normalized.meta == {"provider": "test"}


def test_unsupported_content_fails_fast() -> None:
    with pytest.raises(TypeError, match="Unsupported message content"):
        normalize_content(object())


def test_raw_image_mode_is_revalidated_during_normalization() -> None:
    with pytest.raises(ValueError, match="mode"):
        normalize_content([Image.new("CMYK", (10, 10))])

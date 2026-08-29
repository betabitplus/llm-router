from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from llm_router import FileSchema, VideoSchema, VideoUrlSchema
from llm_router._internal.capabilities.content import (
    MediaPart,
    TextPart,
    normalize_content,
)

pytestmark = [
    pytest.mark.verifies("REQ_MULTIMODAL_CONTENT_NORMALIZATION[revision==1]"),
    pytest.mark.verification_kind("unit"),
]


def test_normalize_content_preserves_text_and_media_order(tmp_path: Path) -> None:
    file_path = tmp_path / "doc.txt"
    file_path.write_text("hello", encoding="utf-8")
    video_path = tmp_path / "clip.mp4"
    video_path.write_bytes(b"video")

    message = normalize_content(
        [
            "lead",
            FileSchema(path=str(file_path), mime_type="text/plain"),
            Image.new("RGB", (10, 12)),
            VideoSchema(path=str(video_path), fps=2),
            VideoUrlSchema(url="https://video.example/clip.mp4"),
            "tail",
        ]
    )

    assert [part.kind for part in message.parts] == [
        "text",
        "media",
        "media",
        "media",
        "media",
        "text",
    ]
    assert isinstance(message.parts[0], TextPart)
    assert isinstance(message.parts[1], MediaPart)
    assert [part.media.kind for part in message.parts[1:5]] == [
        "file",
        "image",
        "video_file",
        "video_url",
    ]


def test_unsupported_content_fails_fast() -> None:
    with pytest.raises(TypeError, match="Unsupported message content"):
        normalize_content(object())


def test_raw_image_mode_is_revalidated_during_normalization() -> None:
    with pytest.raises(ValueError, match="mode"):
        normalize_content([Image.new("CMYK", (10, 10))])

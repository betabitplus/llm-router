from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from llm_router import ChatMessage, FileSchema, VideoSchema, VideoUrlSchema
from llm_router._internal.capabilities.content import (
    MediaPart,
    TextPart,
    normalize_chat_message,
    normalize_content,
)
from llm_router._internal.capabilities.media import (
    FileMedia,
    ImageMedia,
    VideoFileMedia,
    VideoUrlMedia,
)

pytestmark = [
    pytest.mark.verifies("REQ_MULTIMODAL_CONTENT_NORMALIZATION[revision==2]"),
    pytest.mark.verification_kind("unit"),
]


@pytest.mark.coverage_item("VC_CONTENT_ORDER_DESCRIPTOR_METADATA")
def test_normalize_content_preserves_order_and_descriptor_metadata(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "doc.txt"
    file_path.write_text("hello", encoding="utf-8")
    video_path = tmp_path / "clip.mp4"
    video_path.write_bytes(b"video")
    image = Image.new("RGBA", (10, 12))

    message = normalize_content(
        [
            "lead",
            FileSchema(path=str(file_path), mime_type="text/plain"),
            image,
            VideoSchema(
                path=str(video_path),
                fps=2,
                start_offset=1,
                end_offset=5,
            ),
            VideoUrlSchema(
                url="https://video.example/clip.mp4",
                fps=3,
                start_offset=2,
                end_offset=8,
            ),
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
    assert message.parts[0].text == "lead"
    assert isinstance(message.parts[5], TextPart)
    assert message.parts[5].text == "tail"

    media_parts = message.parts[1:5]
    assert all(isinstance(part, MediaPart) for part in media_parts)
    file_media = media_parts[0].media
    image_media = media_parts[1].media
    video_file_media = media_parts[2].media
    video_url_media = media_parts[3].media

    assert isinstance(file_media, FileMedia)
    assert (file_media.path, file_media.mime_type) == (str(file_path), "text/plain")

    assert isinstance(image_media, ImageMedia)
    assert image_media.image is image
    assert (image_media.width, image_media.height, image_media.mode) == (10, 12, "RGBA")

    assert isinstance(video_file_media, VideoFileMedia)
    assert (
        video_file_media.path,
        video_file_media.fps,
        video_file_media.start_offset,
        video_file_media.end_offset,
    ) == (str(video_path), 2, 1, 5)

    assert isinstance(video_url_media, VideoUrlMedia)
    assert (
        video_url_media.url,
        video_url_media.fps,
        video_url_media.start_offset,
        video_url_media.end_offset,
    ) == ("https://video.example/clip.mp4", 3, 2, 8)


@pytest.mark.coverage_item("VC_CONTENT_CHAT_MESSAGE_SEMANTICS")
def test_normalize_chat_message_preserves_role_parts_and_copies_metadata() -> None:
    metadata: dict[str, Any] = {"provider": "google", "attempt": 2}
    source = ChatMessage(
        role="assistant",
        parts=("first", "second"),
        meta=metadata,
    )

    normalized = normalize_chat_message(source)

    assert normalized.role == "assistant"
    assert tuple(
        part.text for part in normalized.parts if isinstance(part, TextPart)
    ) == ("first", "second")
    assert normalized.meta == metadata
    assert normalized.meta is not source.meta

    source.meta["attempt"] = 3
    assert normalized.meta["attempt"] == 2


@pytest.mark.coverage_item("VC_CONTENT_INVALID_INPUT_REJECTION")
@pytest.mark.parametrize(
    ("value", "message"),
    [
        pytest.param(
            object(), "Unsupported message content", id="unsupported-top-level"
        ),
        pytest.param(
            [object()], "Unsupported media value", id="unsupported-media-part"
        ),
        pytest.param([Image.new("CMYK", (10, 10))], "mode", id="invalid-image-mode"),
        pytest.param([Image.new("RGB", (0, 10))], "too small", id="image-too-small"),
        pytest.param(
            [Image.new("RGB", (16385, 1))],
            "too large",
            id="image-too-large",
        ),
    ],
)
def test_invalid_content_is_rejected_locally(value: object, message: str) -> None:
    with pytest.raises((TypeError, ValueError), match=message):
        normalize_content(value)

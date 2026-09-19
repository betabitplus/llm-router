from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from llm_router import FileSchema, VideoSchema, VideoUrlSchema
from llm_router._internal.runtime.errors import SessionSerializationError
from llm_router._internal.session import SessionStore

pytestmark = [
    pytest.mark.verifies("TREQ_SESSION_SERIALIZATION[revision==1]"),
    pytest.mark.verification_kind("unit"),
]


@pytest.mark.coverage_item("VC_SESSION_SERIALIZATION_MEDIA")
def test_save_load_preserves_embedded_file_bytes(tmp_path: Path) -> None:
    file_path = tmp_path / "input.bin"
    file_path.write_bytes(b"file-bytes")
    store = SessionStore()
    store.remember(
        user_content=(
            FileSchema(path=str(file_path), mime_type="application/octet-stream"),
        ),
        assistant_text="done",
    )

    loaded = SessionStore.load(store.save(tmp_path / "session.json"))
    part = loaded.history[0].parts[0]

    assert Path(part.path).read_bytes() == b"file-bytes"
    assert part.mime_type == "application/octet-stream"


@pytest.mark.coverage_item("VC_SESSION_SERIALIZATION_MEDIA")
def test_save_load_preserves_embedded_image_bytes(tmp_path: Path) -> None:
    image = Image.new("RGBA", (3, 2), (12, 34, 56, 78))
    store = SessionStore()
    store.remember(user_content=(image,), assistant_text="done")

    loaded = SessionStore.load(store.save(tmp_path / "session.json"))
    part = loaded.history[0].parts[0]

    assert isinstance(part, Image.Image)
    assert part.mode == "RGBA"
    assert part.size == (3, 2)
    assert part.getpixel((0, 0)) == (12, 34, 56, 78)


@pytest.mark.coverage_item("VC_SESSION_SERIALIZATION_MEDIA")
def test_save_load_preserves_embedded_local_video_bytes_and_metadata(
    tmp_path: Path,
) -> None:
    video_path = tmp_path / "clip.mp4"
    video_path.write_bytes(b"video-bytes")
    store = SessionStore()
    store.remember(
        user_content=(
            VideoSchema(
                path=str(video_path),
                fps=2,
                start_offset=1,
                end_offset=5,
            ),
        ),
        assistant_text="done",
    )

    loaded = SessionStore.load(store.save(tmp_path / "session.json"))
    part = loaded.history[0].parts[0]

    assert Path(part.path).read_bytes() == b"video-bytes"
    assert (part.fps, part.start_offset, part.end_offset) == (2, 1, 5)


@pytest.mark.coverage_item("VC_SESSION_SERIALIZATION_MEDIA")
def test_save_load_preserves_remote_video_descriptor_metadata(tmp_path: Path) -> None:
    store = SessionStore()
    store.remember(
        user_content=(
            VideoUrlSchema(
                url="https://video.example/clip.mp4",
                fps=3,
                start_offset=2,
                end_offset=8,
            ),
        ),
        assistant_text="done",
    )

    loaded = SessionStore.load(store.save(tmp_path / "session.json"))
    part = loaded.history[0].parts[0]

    assert part.url == "https://video.example/clip.mp4"
    assert (part.fps, part.start_offset, part.end_offset) == (3, 2, 8)


@pytest.mark.coverage_item("VC_SESSION_SERIALIZATION_VERSION_REJECTION")
def test_load_rejects_unsupported_serialization_version(tmp_path: Path) -> None:
    path = tmp_path / "session.json"
    path.write_text('{"version": 999, "system": null, "history": []}')

    with pytest.raises(SessionSerializationError, match="Unsupported session"):
        SessionStore.load(path)

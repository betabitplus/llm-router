from __future__ import annotations

from pathlib import Path

import pytest

from llm_router import FileSchema, VideoSchema
from llm_router._internal.runtime.errors import SessionSerializationError
from llm_router._internal.session import SessionStore


def test_save_load_preserves_embedded_media_bytes(tmp_path: Path) -> None:
    file_path = tmp_path / "input.bin"
    file_path.write_bytes(b"file-bytes")
    video_path = tmp_path / "clip.mp4"
    video_path.write_bytes(b"video-bytes")
    store = SessionStore()
    store.remember(
        user_content=(
            FileSchema(path=str(file_path), mime_type="application/octet-stream"),
            VideoSchema(path=str(video_path), fps=2),
        ),
        assistant_text="done",
    )

    loaded = SessionStore.load(store.save(tmp_path / "session.json"))
    parts = loaded.history[0].parts

    assert Path(parts[0].path).read_bytes() == b"file-bytes"
    assert Path(parts[1].path).read_bytes() == b"video-bytes"
    assert parts[1].fps == 2


def test_load_rejects_unsupported_serialization_version(tmp_path: Path) -> None:
    path = tmp_path / "session.json"
    path.write_text('{"version": 999, "system": null, "history": []}')

    with pytest.raises(SessionSerializationError, match="Unsupported session"):
        SessionStore.load(path)

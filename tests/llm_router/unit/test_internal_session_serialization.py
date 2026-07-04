from __future__ import annotations

from pathlib import Path

import pytest

from llm_router import FileSchema, VideoSchema
from llm_router._internal.errors import SessionSerializationError
from llm_router._internal.session import SessionStore


def test_save_load_round_trips_text_history_and_metadata(tmp_path: Path) -> None:
    store = SessionStore(system="system")
    store.remember(
        user_content=("hello", "detail"),
        assistant_text="answer",
        assistant_meta={"usage": {"total_tokens": 3}},
    )

    loaded = SessionStore.load(store.save(tmp_path / "session.json"))

    assert loaded.system == store.system
    assert loaded.history == store.history


def test_save_load_preserves_embedded_file_and_video_bytes(tmp_path: Path) -> None:
    file_path = tmp_path / "input.bin"
    file_path.write_bytes(b"file-bytes")
    video_path = tmp_path / "clip.mp4"
    video_path.write_bytes(b"video-bytes")
    store = SessionStore()
    store.remember(
        user_content=(
            "watch",
            FileSchema(path=str(file_path), mime_type="application/octet-stream"),
            VideoSchema(path=str(video_path), fps=2),
        ),
        assistant_text="done",
    )

    loaded = SessionStore.load(store.save(tmp_path / "session.json"))
    user_parts = loaded.history[0].parts

    assert Path(user_parts[1].path).read_bytes() == b"file-bytes"
    assert user_parts[1].mime_type == "application/octet-stream"
    assert Path(user_parts[2].path).read_bytes() == b"video-bytes"
    assert user_parts[2].fps == 2


def test_load_rejects_unsupported_version(tmp_path: Path) -> None:
    session_path = tmp_path / "session.json"
    session_path.write_text('{"version": 999, "system": null, "history": []}')

    with pytest.raises(SessionSerializationError, match="Unsupported session"):
        SessionStore.load(session_path)


def test_failed_save_does_not_corrupt_existing_file(tmp_path: Path) -> None:
    session_path = tmp_path / "session.json"
    session_path.write_text("original", encoding="utf-8")
    blocker = tmp_path / "blocker"
    blocker.write_text("not a directory", encoding="utf-8")
    store = SessionStore()

    with pytest.raises(SessionSerializationError):
        store.save(blocker / "session.json")

    assert session_path.read_text(encoding="utf-8") == "original"

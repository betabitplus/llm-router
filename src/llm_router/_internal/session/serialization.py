"""Session serialization helpers.

Why:
    Keeps persistent session artifacts provider-neutral and based on public
    conversation semantics.
"""

from __future__ import annotations

import base64
import json
import tempfile
from copy import deepcopy
from io import BytesIO
from pathlib import Path

from PIL import Image

from llm_router._api.contracts import (
    ChatMessage,
    ChatPart,
    FileSchema,
    VideoSchema,
    VideoUrlSchema,
)
from llm_router._internal.errors import SessionSerializationError

_SESSION_VERSION = 1


# =============================================================================
# Public Helpers
# =============================================================================


def encode_session(*, system: str | None, history: tuple[ChatMessage, ...]) -> str:
    """Return a JSON session artifact containing only public semantics."""
    payload = {
        "version": _SESSION_VERSION,
        "system": system,
        "history": [_encode_message(message) for message in history],
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def decode_session(text: str) -> tuple[str | None, tuple[ChatMessage, ...]]:
    """Decode a JSON session artifact into provider-neutral chat messages."""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        msg = "Session file is not valid JSON."
        raise SessionSerializationError(msg) from exc

    if not isinstance(payload, dict):
        msg = "Session payload must be a JSON object."
        raise SessionSerializationError(msg)
    if payload.get("version") != _SESSION_VERSION:
        msg = "Unsupported session file version."
        raise SessionSerializationError(msg)

    system = payload.get("system")
    if system is not None and not isinstance(system, str):
        msg = "Session system prompt must be a string or null."
        raise SessionSerializationError(msg)

    raw_history = payload.get("history")
    if not isinstance(raw_history, list):
        msg = "Session history must be a list."
        raise SessionSerializationError(msg)

    return system, tuple(_decode_message(item) for item in raw_history)


def atomic_write_text(path: str | Path, text: str) -> Path:
    """Write a session artifact with same-directory atomic replacement."""
    target = Path(path)
    temp_path: Path | None = None
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=target.parent,
            delete=False,
            prefix=f".{target.name}.",
            suffix=".tmp",
        ) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(text)
            temp_file.flush()
        temp_path.replace(target)
    except OSError as exc:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        msg = f"Could not save session to {target}."
        raise SessionSerializationError(msg) from exc
    return target


# =============================================================================
# Encoding
# =============================================================================


def _encode_message(message: ChatMessage) -> dict[str, object]:
    """Encode one public chat message."""
    return {
        "role": message.role,
        "parts": [_encode_part(part) for part in message.parts],
        "meta": deepcopy(message.meta),
    }


def _encode_part(part: ChatPart) -> dict[str, object]:
    """Encode one public chat part without provider-native payloads."""
    if isinstance(part, str):
        return {"kind": "text", "text": part}
    if isinstance(part, FileSchema):
        return {
            "kind": "file",
            "name": Path(part.path).name,
            "bytes": _read_bytes_b64(Path(part.path)),
            "mime_type": part.mime_type,
        }
    if isinstance(part, VideoSchema):
        return {
            "kind": "video",
            "name": Path(part.path).name,
            "bytes": _read_bytes_b64(Path(part.path)),
            "fps": part.fps,
            "start_offset": part.start_offset,
            "end_offset": part.end_offset,
        }
    if isinstance(part, VideoUrlSchema):
        return {
            "kind": "video_url",
            "url": part.url,
            "fps": part.fps,
            "start_offset": part.start_offset,
            "end_offset": part.end_offset,
        }
    return {
        "kind": "image",
        "mode": part.mode,
        "bytes": _image_b64(part),
    }


def _read_bytes_b64(path: Path) -> str:
    """Return base64 file bytes for a local media reference."""
    try:
        return base64.b64encode(path.read_bytes()).decode("ascii")
    except OSError as exc:
        msg = f"Could not read session media file {path}."
        raise SessionSerializationError(msg) from exc


def _image_b64(image: Image.Image) -> str:
    """Return base64 PNG bytes for an in-memory image."""
    with BytesIO() as buffer:
        image.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("ascii")


# =============================================================================
# Decoding
# =============================================================================


def _decode_message(item: object) -> ChatMessage:
    """Decode one persisted chat message."""
    if not isinstance(item, dict):
        msg = "Session history entries must be objects."
        raise SessionSerializationError(msg)
    role = item.get("role")
    if role not in {"user", "assistant"}:
        msg = "Session message role is invalid."
        raise SessionSerializationError(msg)
    parts = item.get("parts")
    if not isinstance(parts, list):
        msg = "Session message parts must be a list."
        raise SessionSerializationError(msg)
    meta = item.get("meta")
    if meta is None:
        meta = {}
    if not isinstance(meta, dict):
        msg = "Session message metadata must be an object."
        raise SessionSerializationError(msg)
    return ChatMessage(
        role=role,
        parts=tuple(_decode_part(part) for part in parts),
        meta=deepcopy(meta),
    )


def _decode_part(item: object) -> ChatPart:
    """Decode one persisted chat part."""
    if not isinstance(item, dict):
        msg = "Session part entries must be objects."
        raise SessionSerializationError(msg)

    kind = item.get("kind")
    if kind == "text":
        text = item.get("text")
        if not isinstance(text, str):
            msg = "Session text part must contain text."
            raise SessionSerializationError(msg)
        return text
    if kind == "file":
        return FileSchema(
            path=str(_materialize_bytes(item, default_suffix=".bin")),
            mime_type=_optional_str(item.get("mime_type")),
        )
    if kind == "video":
        return VideoSchema(
            path=str(_materialize_bytes(item, default_suffix=".mp4")),
            fps=_required_int(item.get("fps"), field_name="fps"),
            start_offset=_optional_int(item.get("start_offset")),
            end_offset=_optional_int(item.get("end_offset")),
        )
    if kind == "video_url":
        url = item.get("url")
        if not isinstance(url, str):
            msg = "Session video URL part must contain a URL."
            raise SessionSerializationError(msg)
        return VideoUrlSchema(
            url=url,
            fps=_required_int(item.get("fps"), field_name="fps"),
            start_offset=_optional_int(item.get("start_offset")),
            end_offset=_optional_int(item.get("end_offset")),
        )
    if kind == "image":
        return _decode_image(item)

    msg = "Session part kind is invalid."
    raise SessionSerializationError(msg)


def _materialize_bytes(item: dict[str, object], *, default_suffix: str) -> Path:
    """Materialize embedded media bytes for public DTO validation."""
    raw_bytes = _decode_b64(item.get("bytes"))
    name = item.get("name")
    suffix = Path(name).suffix if isinstance(name, str) and Path(name).suffix else ""
    media_dir = Path(tempfile.mkdtemp(prefix="llm-router-session-media-"))
    path = media_dir / f"part{suffix or default_suffix}"
    path.write_bytes(raw_bytes)
    return path


def _decode_image(item: dict[str, object]) -> Image.Image:
    """Decode an embedded PNG image into a Pillow image."""
    image_bytes = _decode_b64(item.get("bytes"))
    try:
        image = Image.open(BytesIO(image_bytes))
        image.load()
    except OSError as exc:
        msg = "Session image part is invalid."
        raise SessionSerializationError(msg) from exc
    return image


def _decode_b64(value: object) -> bytes:
    """Decode a required base64 string field."""
    if not isinstance(value, str):
        msg = "Session media bytes must be a base64 string."
        raise SessionSerializationError(msg)
    try:
        return base64.b64decode(value.encode("ascii"), validate=True)
    except (ValueError, UnicodeEncodeError) as exc:
        msg = "Session media bytes are invalid."
        raise SessionSerializationError(msg) from exc


def _optional_str(value: object) -> str | None:
    """Decode an optional string field."""
    if value is None or isinstance(value, str):
        return value
    msg = "Session optional string field is invalid."
    raise SessionSerializationError(msg)


def _optional_int(value: object) -> int | None:
    """Decode an optional integer field."""
    if value is None:
        return None
    return _required_int(value, field_name="optional integer")


def _required_int(value: object, *, field_name: str) -> int:
    """Decode a required integer field."""
    if isinstance(value, int):
        return value
    msg = f"Session {field_name} field must be an integer."
    raise SessionSerializationError(msg)

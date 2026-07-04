"""Provider-neutral content normalization.

Why:
    Keeps public message-content handling separate from concrete provider
    payload construction.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from llm_router._api.contracts import ChatMessage, ChatPart, ChatRole
from llm_router._internal.capabilities.media import (
    MediaDescriptor,
    describe_media,
)


@dataclass(frozen=True, slots=True)
class TextPart:
    """Normalized text message part."""

    kind: Literal["text"]
    text: str


@dataclass(frozen=True, slots=True)
class MediaPart:
    """Normalized media message part."""

    kind: Literal["media"]
    media: MediaDescriptor


NormalizedPart = TextPart | MediaPart


@dataclass(frozen=True, slots=True)
class NormalizedMessage:
    """Provider-neutral message with stable role and ordered parts."""

    role: str
    parts: tuple[NormalizedPart, ...]
    meta: dict[str, object]


def normalize_content(content: object, *, role: ChatRole = "user") -> NormalizedMessage:
    """Normalize role-less public content into one provider-neutral message."""
    return NormalizedMessage(
        role=role,
        parts=normalize_parts(_content_parts(content)),
        meta={},
    )


def normalize_chat_message(message: ChatMessage) -> NormalizedMessage:
    """Normalize a public chat transcript message."""
    return NormalizedMessage(
        role=message.role,
        parts=normalize_parts(message.parts),
        meta=dict(message.meta),
    )


def normalize_parts(parts: Sequence[ChatPart]) -> tuple[NormalizedPart, ...]:
    """Normalize public message parts while preserving caller order."""
    normalized: list[NormalizedPart] = []
    for part in parts:
        if isinstance(part, str):
            normalized.append(TextPart(kind="text", text=part))
        else:
            normalized.append(MediaPart(kind="media", media=describe_media(part)))
    return tuple(normalized)


def _content_parts(content: object) -> tuple[ChatPart, ...]:
    """Return public content as ordered parts."""
    if isinstance(content, str):
        return (content,)
    if isinstance(content, Sequence) and not isinstance(content, bytes | bytearray):
        return tuple(content)

    msg = f"Unsupported message content: {type(content).__name__}."
    raise TypeError(msg)

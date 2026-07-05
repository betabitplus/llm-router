"""Provider-neutral session store.

Why:
    Provides the private storage object consumed by the public `Session` facade
    while later phases add semantic persistence and message assembly.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from llm_router._internal.contracts.models import ChatMessage, ChatPart, MessageContent
from llm_router._internal.runtime.errors import SessionSerializationError
from llm_router._internal.session.serialization import (
    atomic_write_text,
    decode_session,
    encode_session,
)
from py_lib_runtime import get_logger

logger = get_logger(__name__)


class SessionStore:
    """Private provider-neutral session state."""

    def __init__(self, system: str | None = None) -> None:
        """Create an empty session store."""
        self._system = system
        self._history: tuple[ChatMessage, ...] = ()

    @property
    def system(self) -> str | None:
        """Return the session-level system prompt."""
        return self._system

    @property
    def history(self) -> tuple[ChatMessage, ...]:
        """Return an immutable history snapshot."""
        return self._history

    @classmethod
    def load(cls, path: str | Path) -> SessionStore:
        """Load a session artifact."""
        session_path = Path(path)
        try:
            text = session_path.read_text(encoding="utf-8")
        except OSError as exc:
            msg = f"Could not load session from {session_path}."
            raise SessionSerializationError(msg) from exc
        system, history = decode_session(text)
        loaded = cls(system=system)
        loaded._history = tuple(_copy_message(message) for message in history)
        logger.info(
            "Session loaded",
            event_type="llm_router.session.loaded",
            history_count=len(loaded._history),
            path=str(session_path),
        )
        return loaded

    def clear(self) -> None:
        """Clear stored history."""
        self._history = ()
        logger.info(
            "Session cleared",
            event_type="llm_router.session.cleared",
            has_system=self._system is not None,
        )

    def fork(self) -> SessionStore:
        """Return an independent copy of this store."""
        forked = type(self)(system=self._system)
        forked._history = tuple(_copy_message(message) for message in self._history)
        logger.info(
            "Session forked",
            event_type="llm_router.session.forked",
            history_count=len(self._history),
        )
        return forked

    def build_messages(
        self,
        user_content: str | MessageContent,
        *,
        include_history: bool = True,
    ) -> list[ChatPart]:
        """Build outgoing transcript parts for one user turn."""
        messages: list[ChatPart] = []
        if self._system:
            messages.append(self._system)

        if include_history:
            for message in self._history:
                messages.extend(_format_message_for_prompt(message))

        messages.extend(_format_user_parts(_as_parts(user_content)))
        return messages

    def remember(
        self,
        user_content: str | MessageContent,
        assistant_text: str,
        assistant_meta: dict[str, Any] | None = None,
    ) -> None:
        """Append one user/assistant turn to history."""
        user_message = ChatMessage(
            role="user",
            parts=_copy_parts(_as_parts(user_content)),
        )
        assistant_message = ChatMessage(
            role="assistant",
            parts=(assistant_text,),
            meta=deepcopy({} if assistant_meta is None else assistant_meta),
        )
        self._history = (*self._history, user_message, assistant_message)
        logger.info(
            "Session turn remembered",
            event_type="llm_router.session.turn.remembered",
            history_count=len(self._history),
            has_assistant_meta=bool(assistant_message.meta),
        )

    def save(self, path: str | Path) -> Path:
        """Persist a session artifact."""
        saved_path = atomic_write_text(
            path,
            encode_session(system=self._system, history=self._history),
        )
        logger.info(
            "Session saved",
            event_type="llm_router.session.saved",
            history_count=len(self._history),
            path=str(saved_path),
        )
        return saved_path


# =============================================================================
# Helpers
# =============================================================================


def _as_parts(user_content: str | MessageContent) -> tuple[ChatPart, ...]:
    """Normalize public user content into a tuple of chat parts."""
    if isinstance(user_content, str):
        return (user_content,)
    return tuple(user_content)


def _copy_parts(parts: tuple[ChatPart, ...]) -> tuple[ChatPart, ...]:
    """Copy public chat parts so stored history does not alias caller input."""
    return tuple(deepcopy(part) for part in parts)


def _copy_message(message: ChatMessage) -> ChatMessage:
    """Copy one public chat message without sharing mutable metadata."""
    return ChatMessage(
        role=message.role,
        parts=_copy_parts(message.parts),
        meta=deepcopy(message.meta),
    )


def _format_message_for_prompt(message: ChatMessage) -> list[ChatPart]:
    """Format one stored message for the public transcript view."""
    if message.role == "user":
        return _format_user_parts(message.parts)
    assistant_text = "" if not message.parts else str(message.parts[0])
    return [f"Assistant: {assistant_text}", *message.parts[1:]]


def _format_user_parts(parts: tuple[ChatPart, ...]) -> list[ChatPart]:
    """Format public user parts with the readable transcript label."""
    if parts and isinstance(parts[0], str):
        return [f"User: {parts[0]}", *parts[1:]]
    return ["User:", *parts]

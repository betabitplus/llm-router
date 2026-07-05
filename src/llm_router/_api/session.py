"""Public session facade for `llm_router`.

Why:
    Provides a provider-agnostic continuity boundary for conversation state,
    persistence, and branching.

How:
    Keep the caller-facing session surface here while private storage,
    serialization, and transcript assembly stay in the internal store layer.

Notes:
    Sessions intentionally speak the public API's role-less content language at
    the boundary, but store a role-based internal transcript.

    Important public behaviors:
    - a session can be attached to any `LLMRouter`
    - the session is provider-agnostic and can be saved, loaded, and forked
    - saved sessions are self-contained snapshots, including persisted media
      references and assistant metadata
    - `build_messages()` is for inspection or advanced workflows, not the main
      provider payload format
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from llm_router._api.types import ChatMessage, ChatPart, MessageContent
from llm_router._internal import SessionStore


class Session:
    """Provider-agnostic public session facade.

    A `Session` represents conversation continuity independent of any single
    provider SDK. It can be reused across multiple router calls, saved to disk,
    loaded back later, and forked into independent branches.

    The session stores:
    - an optional system prompt
    - role-based transcript history
    - optional assistant metadata such as provider, model, usage, routing
      trace, and tool trace
    """

    def __init__(self, *, system: str | None = None) -> None:
        """Create a new public session.

        Args:
            system:
                Optional system instruction remembered as part of the session's
                long-lived conversation state.
        """
        self._store = SessionStore(system=system)

    @property
    def system(self) -> str | None:
        """Return the session-level system prompt, if one was set."""
        return self._store.system

    @property
    def history(self) -> tuple[ChatMessage, ...]:
        """Return the immutable conversation history.

        The returned value is a snapshot-style tuple of public `ChatMessage`
        objects. Mutating nested values inside a message's `meta` payload is
        still the caller's responsibility.
        """
        return self._store.history

    @classmethod
    def _from_store(cls, store: SessionStore) -> Session:
        """Create a facade from an existing private store."""
        obj = cls.__new__(cls)
        obj._store = store
        return obj

    @classmethod
    def load(cls, path: str | Path) -> Session:
        """Load a previously saved session snapshot from disk.

        Loaded sessions are ready to attach directly to a new `LLMRouter`.
        """
        return cls._from_store(SessionStore.load(path))

    def clear(self) -> None:
        """Clear stored history while keeping the session object itself."""
        self._store.clear()

    def fork(self) -> Session:
        """Fork the current session into an independent branch.

        The new session starts with the same system prompt and history, but
        future turns diverge independently.
        """
        return self._from_store(self._store.fork())

    def build_messages(
        self,
        user_content: str | MessageContent,
        *,
        include_history: bool = True,
    ) -> list[ChatPart]:
        """Build outgoing transcript parts for one user turn.

        This returns the session's transcript-oriented public view of the next
        request. It is mainly useful for inspection, debugging, and advanced
        workflows that need to see the assembled chat context.
        """
        return self._store.build_messages(
            user_content=user_content,
            include_history=include_history,
        )

    def remember(
        self,
        *,
        user_content: str | MessageContent,
        assistant_text: str,
        assistant_meta: dict[str, Any] | None = None,
    ) -> None:
        """Append one user/assistant turn to the session history.

        This is normally done automatically by `LLMRouter` after a successful
        request. Call it directly only when you are manually managing a session
        outside the router facade.
        """
        self._store.remember(
            user_content=user_content,
            assistant_text=assistant_text,
            assistant_meta=assistant_meta,
        )

    def save(self, path: str | Path) -> Path:
        """Persist the session to disk and return the written path.

        The saved file is a reusable session artifact, not just a debug dump.
        It is designed to be loaded later without requiring the original
        in-memory objects to still exist.
        """
        return self._store.save(path)

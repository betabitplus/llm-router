from __future__ import annotations

from llm_router._internal.session import SessionStore


def test_remember_builds_alternating_public_history() -> None:
    store = SessionStore(system="system")

    store.remember(
        user_content=("hello", "detail"),
        assistant_text="answer",
        assistant_meta={"provider": "test"},
    )

    assert store.history[0].role == "user"
    assert store.history[0].parts == ("hello", "detail")
    assert store.history[1].role == "assistant"
    assert store.history[1].parts == ("answer",)
    assert store.history[1].meta == {"provider": "test"}
    assert store.build_messages("next") == [
        "system",
        "User: hello",
        "detail",
        "Assistant: answer",
        "User: next",
    ]


def test_build_messages_without_history_keeps_system_and_current_turn_only() -> None:
    store = SessionStore(system="system")
    store.remember(user_content="old", assistant_text="answer")

    assert store.build_messages("new", include_history=False) == [
        "system",
        "User: new",
    ]


def test_non_text_first_content_uses_standalone_label() -> None:
    marker = object()
    store = SessionStore()

    assert store.build_messages((marker, "tail"), include_history=False) == [
        "User:",
        marker,
        "tail",
    ]


def test_remember_copies_metadata_input() -> None:
    store = SessionStore()
    meta = {"usage": {"total_tokens": 1}}

    store.remember(user_content="hello", assistant_text="answer", assistant_meta=meta)
    meta["usage"]["total_tokens"] = 2

    assert store.history[-1].meta == {"usage": {"total_tokens": 1}}


def test_clear_keeps_system_and_session_reusable() -> None:
    store = SessionStore(system="system")
    store.remember(user_content="hello", assistant_text="answer")

    store.clear()
    store.remember(user_content="new", assistant_text="fresh")

    assert store.system == "system"
    assert len(store.history) == 2
    assert store.history[0].parts == ("new",)


def test_fork_starts_equal_and_diverges_independently() -> None:
    store = SessionStore(system="system")
    store.remember(user_content="hello", assistant_text="answer")

    forked = store.fork()
    forked.remember(user_content="branch", assistant_text="branch answer")

    assert store.history != forked.history
    assert len(store.history) == 2
    assert len(forked.history) == 4

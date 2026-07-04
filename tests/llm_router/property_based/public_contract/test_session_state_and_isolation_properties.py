"""Property-based tests for session state and isolation invariants.

Why:
    Protects the library's provider-agnostic continuity rules through many
    generated conversation shapes.

How:
    Exercises only the supported public `Session` facade so the invariants stay
    valid even if the private storage implementation changes completely.
"""

from __future__ import annotations

import tempfile
from collections.abc import Sequence
from pathlib import Path

from hypothesis import given, settings, strategies as st

from llm_router import FileSchema, Session, VideoSchema, VideoUrlSchema

# =============================================================================
# Strategies
# =============================================================================


_TEXT = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789 _-",
    min_size=0,
    max_size=24,
)
_NONEMPTY_TEXT = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789 _-",
    min_size=1,
    max_size=24,
)
_OPTIONAL_SYSTEM = st.one_of(st.none(), _TEXT)
_SAFE_NAME = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789_-",
    min_size=1,
    max_size=12,
)
type _USER_CONTENT = str | tuple[str, ...]
_USER_CONTENT_STRATEGY = st.one_of(
    _TEXT,
    st.lists(_TEXT, min_size=1, max_size=4).map(tuple),
)
_ASSISTANT_META = st.dictionaries(
    keys=st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz0123456789_-",
        min_size=1,
        max_size=12,
    ),
    values=st.one_of(
        _TEXT,
        st.integers(min_value=-5, max_value=5),
        st.booleans(),
    ),
    max_size=3,
)
_TURN = st.tuples(_USER_CONTENT_STRATEGY, _TEXT, _ASSISTANT_META)
_TEXT_ONLY_TURN = st.tuples(
    _USER_CONTENT_STRATEGY,
    _TEXT,
    _ASSISTANT_META,
)


# =============================================================================
# Helpers
# =============================================================================


def _expected_user_parts(user_content: _USER_CONTENT) -> tuple[str, ...]:
    """Return the public user parts tuple implied by one turn input."""
    if isinstance(user_content, str):
        return (user_content,)
    return tuple(user_content)


def _apply_turns(
    session: Session,
    turns: list[tuple[_USER_CONTENT, str, dict[str, object]]],
) -> None:
    """Remember a generated list of public turns in order."""
    # Keeping turn application in one helper makes each property read more like
    # a scenario description: arrange history, perform one operation, check the
    # resulting public invariant.
    for user_content, assistant_text, assistant_meta in turns:
        session.remember(
            user_content=user_content,
            assistant_text=assistant_text,
            assistant_meta=assistant_meta,
        )


def _build_multimodal_content(
    *,
    temp_dir: Path,
    leading_text: str | None,
    middle_text: str,
    file_name: str,
    file_data: bytes,
    video_name: str,
    video_data: bytes,
    host: str,
    fps: int,
    start_offset: int | None,
    end_offset: int | None,
) -> tuple[object, ...]:
    """Create one generated multimodal content bundle using public wrappers."""
    file_path = temp_dir / f"{file_name}.bin"
    file_path.write_bytes(file_data)

    video_path = temp_dir / f"{video_name}.mp4"
    video_path.write_bytes(video_data)

    parts: list[object] = []
    if leading_text is not None:
        parts.append(leading_text)
    parts.append(FileSchema(path=str(file_path)))
    if middle_text:
        parts.append(middle_text)
    parts.append(
        VideoSchema(
            path=str(video_path),
            fps=fps,
            start_offset=start_offset,
            end_offset=end_offset,
        )
    )
    parts.append(
        VideoUrlSchema(
            url=f"https://{host}.example/video",
            fps=fps,
            start_offset=start_offset,
            end_offset=end_offset,
        )
    )
    return tuple(parts)


def _normalize_part(part: object) -> tuple[object, ...]:
    """Normalize public chat parts for cross-session semantic comparison."""
    if isinstance(part, str):
        return ("text", part)
    if isinstance(part, FileSchema):
        return (
            "file",
            Path(part.path).read_bytes(),
            part.mime_type or "application/octet-stream",
        )
    if isinstance(part, VideoSchema):
        return (
            "video",
            Path(part.path).read_bytes(),
            part.fps,
            part.start_offset,
            part.end_offset,
        )
    if isinstance(part, VideoUrlSchema):
        return (
            "video_url",
            part.url,
            part.fps,
            part.start_offset,
            part.end_offset,
        )
    msg = f"Unexpected chat part type: {type(part)!r}"
    raise AssertionError(msg)


def _normalize_parts(parts: Sequence[object]) -> tuple[tuple[object, ...], ...]:
    """Normalize one transcript or message parts sequence."""
    return tuple(_normalize_part(part) for part in parts)


# =============================================================================
# Assertions
# =============================================================================


def assert_turn_pair(
    *,
    user_message: object,
    assistant_message: object,
    user_content: _USER_CONTENT,
    assistant_text: str,
    assistant_meta: dict[str, object],
) -> None:
    """Assert one public user/assistant turn pair in session history."""
    assert user_message.role == "user"
    assert user_message.parts == _expected_user_parts(user_content)
    assert user_message.meta == {}

    assert assistant_message.role == "assistant"
    assert assistant_message.parts == (assistant_text,)
    assert assistant_message.meta == assistant_meta


def assert_multimodal_prompt_tail(
    *,
    built: list[object],
    system: str | None,
    expected_label: str,
    expected_tail: Sequence[object],
) -> None:
    """Assert the user-turn tail of one built multimodal prompt."""
    prefix_len = 1 if system else 0
    if system:
        assert built[0] == system
    assert built[prefix_len] == expected_label
    assert _normalize_parts(built[prefix_len + 1 :]) == _normalize_parts(expected_tail)


# =============================================================================
# Properties
# =============================================================================


@given(system=_OPTIONAL_SYSTEM, turns=st.lists(_TURN, max_size=6))
def test_session_remember_produces_alternating_public_history(
    *,
    system: str | None,
    turns: list[tuple[_USER_CONTENT, str, dict[str, object]]],
) -> None:
    """Remembered turns should appear as alternating public user/assistant pairs."""
    session = Session(system=system)
    _apply_turns(session, turns)

    history = session.history

    # Each public `remember()` call represents one complete conversational
    # turn, so history should always grow in user/assistant pairs.
    assert len(history) == len(turns) * 2
    for index, (user_content, assistant_text, assistant_meta) in enumerate(turns):
        user_message = history[index * 2]
        assistant_message = history[index * 2 + 1]

        # The user side keeps only the caller content; assistant metadata should
        # never leak backward into the user record.
        # The assistant side should preserve both the text and the explicit
        # metadata the caller or router attached to that response.
        assert_turn_pair(
            user_message=user_message,
            assistant_message=assistant_message,
            user_content=user_content,
            assistant_text=assistant_text,
            assistant_meta=assistant_meta,
        )


@given(
    system=_OPTIONAL_SYSTEM,
    prior_turns=st.lists(_TURN, max_size=5),
    current_content=_USER_CONTENT_STRATEGY,
)
def test_build_messages_without_history_depends_only_on_system_and_current_turn(
    *,
    system: str | None,
    prior_turns: list[tuple[_USER_CONTENT, str, dict[str, object]]],
    current_content: _USER_CONTENT,
) -> None:
    """`include_history=False` should ignore previously remembered turns."""
    session = Session(system=system)
    _apply_turns(session, prior_turns)

    fresh = Session(system=system)

    # This comparison is the heart of the property: when history is disabled,
    # a session with old turns should behave like a fresh session with the same
    # system prompt for the current user turn.
    without_history = session.build_messages(current_content, include_history=False)
    fresh_without_history = fresh.build_messages(
        current_content,
        include_history=False,
    )
    assert without_history == fresh_without_history

    # With history enabled, the assembled prompt may grow, but it should never
    # become smaller than the history-free view of the same current turn.
    with_history = session.build_messages(current_content, include_history=True)
    assert len(with_history) >= len(without_history)


@given(
    system=_OPTIONAL_SYSTEM,
    prior_turns=st.lists(_TEXT_ONLY_TURN, max_size=4),
    current_content=_USER_CONTENT_STRATEGY,
)
def test_build_messages_with_history_keeps_public_transcript_order(
    *,
    system: str | None,
    prior_turns: list[tuple[_USER_CONTENT, str, dict[str, object]]],
    current_content: _USER_CONTENT,
) -> None:
    """History-inclusive messages should preserve the public transcript order."""
    session = Session(system=system)
    _apply_turns(session, prior_turns)

    built = session.build_messages(current_content, include_history=True)

    # This test protects the readable transcript semantics exposed by the
    # public session facade: optional system prompt first, then prior user /
    # assistant turns in order, then the current user turn last.
    expected_prefix: list[str] = []
    if system:
        expected_prefix.append(system)

    for user_content, assistant_text, _assistant_meta in prior_turns:
        user_parts = _expected_user_parts(user_content)
        expected_prefix.append(f"User: {user_parts[0]}")
        expected_prefix.extend(list(user_parts[1:]))
        expected_prefix.append(f"Assistant: {assistant_text}")

    current_parts = _expected_user_parts(current_content)
    expected_suffix = [f"User: {current_parts[0]}", *list(current_parts[1:])]

    expected = expected_prefix + expected_suffix
    assert built == expected


@given(
    system=_OPTIONAL_SYSTEM,
    middle_text=_TEXT,
    file_name=_SAFE_NAME,
    file_data=st.binary(max_size=32),
    video_name=_SAFE_NAME,
    video_data=st.binary(max_size=48),
    host=_SAFE_NAME,
    fps=st.integers(min_value=1, max_value=5),
    start_offset=st.one_of(st.none(), st.integers(min_value=0, max_value=20)),
    end_offset=st.one_of(st.none(), st.integers(min_value=0, max_value=20)),
)
@settings(max_examples=25, deadline=None)
def test_build_messages_with_non_text_first_content_uses_standalone_label(
    *,
    system: str | None,
    middle_text: str,
    file_name: str,
    file_data: bytes,
    video_name: str,
    video_data: bytes,
    host: str,
    fps: int,
    start_offset: int | None,
    end_offset: int | None,
) -> None:
    """Non-text-first multimodal turns should keep the label separate."""
    with tempfile.TemporaryDirectory() as temp_dir:
        content = _build_multimodal_content(
            temp_dir=Path(temp_dir),
            leading_text=None,
            middle_text=middle_text,
            file_name=file_name,
            file_data=file_data,
            video_name=video_name,
            video_data=video_data,
            host=host,
            fps=fps,
            start_offset=start_offset,
            end_offset=end_offset,
        )
        session = Session(system=system)

        built = session.build_messages(content, include_history=False)

        # This is the key multimodal transcript rule: when the first user part
        # is media, the label is emitted as its own text part and the original
        # media ordering is preserved unchanged behind it.
        assert_multimodal_prompt_tail(
            built=built,
            system=system,
            expected_label="User:",
            expected_tail=content,
        )


@given(
    system=_OPTIONAL_SYSTEM,
    leading_text=_NONEMPTY_TEXT,
    middle_text=_TEXT,
    file_name=_SAFE_NAME,
    file_data=st.binary(max_size=32),
    video_name=_SAFE_NAME,
    video_data=st.binary(max_size=48),
    host=_SAFE_NAME,
    fps=st.integers(min_value=1, max_value=5),
    start_offset=st.one_of(st.none(), st.integers(min_value=0, max_value=20)),
    end_offset=st.one_of(st.none(), st.integers(min_value=0, max_value=20)),
)
@settings(max_examples=25, deadline=None)
def test_build_messages_with_text_first_multimodal_content_keeps_tail_parts(
    *,
    system: str | None,
    leading_text: str,
    middle_text: str,
    file_name: str,
    file_data: bytes,
    video_name: str,
    video_data: bytes,
    host: str,
    fps: int,
    start_offset: int | None,
    end_offset: int | None,
) -> None:
    """Text-first multimodal turns should fold only the first text into the label."""
    with tempfile.TemporaryDirectory() as temp_dir:
        content = _build_multimodal_content(
            temp_dir=Path(temp_dir),
            leading_text=leading_text,
            middle_text=middle_text,
            file_name=file_name,
            file_data=file_data,
            video_name=video_name,
            video_data=video_data,
            host=host,
            fps=fps,
            start_offset=start_offset,
            end_offset=end_offset,
        )
        session = Session(system=system)

        built = session.build_messages(content, include_history=False)

        # When the first part is text, only that first part is folded into the
        # `"User: ..."` label. The rest of the multimodal bundle must stay in
        # the original order.
        assert_multimodal_prompt_tail(
            built=built,
            system=system,
            expected_label=f"User: {leading_text}",
            expected_tail=content[1:],
        )


@given(
    system=_OPTIONAL_SYSTEM,
    prior_turns=st.lists(_TURN, max_size=5),
    extra_turn=_TURN,
)
def test_fork_starts_equal_and_then_diverges_independently(
    *,
    system: str | None,
    prior_turns: list[tuple[_USER_CONTENT, str, dict[str, object]]],
    extra_turn: tuple[_USER_CONTENT, str, dict[str, object]],
) -> None:
    """Forked sessions should start equal and diverge after later mutation."""
    session = Session(system=system)
    _apply_turns(session, prior_turns)

    forked = session.fork()
    original_history = session.history

    # Forking should snapshot the same public continuity state at the moment of
    # the branch.
    assert forked.system == session.system
    assert forked.history == original_history

    user_content, assistant_text, assistant_meta = extra_turn
    forked.remember(
        user_content=user_content,
        assistant_text=assistant_text,
        assistant_meta=assistant_meta,
    )

    # After the branch mutates, the original session must remain unchanged.
    assert session.history == original_history
    assert len(forked.history) == len(original_history) + 2
    assert forked.history[: len(original_history)] == original_history


@given(
    system=_OPTIONAL_SYSTEM,
    user_content=_USER_CONTENT_STRATEGY,
    assistant_text=_TEXT,
    assistant_meta=_ASSISTANT_META,
)
def test_remember_copies_assistant_meta_input_before_storing(
    *,
    system: str | None,
    user_content: _USER_CONTENT,
    assistant_text: str,
    assistant_meta: dict[str, object],
) -> None:
    """Stored assistant metadata should not alias the caller's input dict."""
    session = Session(system=system)
    original_meta = dict(assistant_meta)

    session.remember(
        user_content=user_content,
        assistant_text=assistant_text,
        assistant_meta=assistant_meta,
    )
    assistant_meta["__later__"] = "changed"

    # The session should snapshot the explicit metadata supplied for that turn
    # instead of leaving stored history vulnerable to later caller mutation.
    assert session.history[-1].meta == original_meta


@given(
    system=_OPTIONAL_SYSTEM,
    prior_turns=st.lists(_TURN, max_size=5),
    new_turn=_TURN,
)
def test_clear_empties_history_and_keeps_session_reusable(
    *,
    system: str | None,
    prior_turns: list[tuple[_USER_CONTENT, str, dict[str, object]]],
    new_turn: tuple[_USER_CONTENT, str, dict[str, object]],
) -> None:
    """Clearing should empty history without making the session unusable."""
    session = Session(system=system)
    _apply_turns(session, prior_turns)

    session.clear()

    # `clear()` is a reset of continuity, not destruction of the session
    # object. The system prompt and future usability should remain intact.
    assert session.history == ()
    assert session.system == system

    user_content, assistant_text, assistant_meta = new_turn
    session.remember(
        user_content=user_content,
        assistant_text=assistant_text,
        assistant_meta=assistant_meta,
    )

    # A cleared session should accept new turns exactly like a fresh session.
    assert len(session.history) == 2
    assert session.history[0].role == "user"
    assert session.history[1].role == "assistant"


@given(
    system=_OPTIONAL_SYSTEM,
    prior_turns=st.lists(_TURN, max_size=5),
    extra_turn=_TURN,
)
def test_history_property_returns_a_snapshot_unchanged_by_later_operations(
    *,
    system: str | None,
    prior_turns: list[tuple[_USER_CONTENT, str, dict[str, object]]],
    extra_turn: tuple[_USER_CONTENT, str, dict[str, object]],
) -> None:
    """Previously captured history tuples should stay stable after later changes."""
    session = Session(system=system)
    _apply_turns(session, prior_turns)

    snapshot = session.history
    expected_snapshot = tuple(snapshot)
    user_content, assistant_text, assistant_meta = extra_turn
    session.remember(
        user_content=user_content,
        assistant_text=assistant_text,
        assistant_meta=assistant_meta,
    )
    session.clear()

    # `history` is documented as a snapshot-style tuple. Later mutations of
    # the session may change future reads, but they should not retroactively
    # rewrite a previously captured snapshot.
    assert len(snapshot) == len(prior_turns) * 2
    assert snapshot == expected_snapshot


@given(system=_OPTIONAL_SYSTEM, turns=st.lists(_TEXT_ONLY_TURN, max_size=5))
@settings(max_examples=30, deadline=None)
def test_save_load_preserves_text_only_public_session_state(
    *,
    system: str | None,
    turns: list[tuple[_USER_CONTENT, str, dict[str, object]]],
) -> None:
    """Saving then loading should preserve public text-only session state."""
    session = Session(system=system)
    _apply_turns(session, turns)

    with tempfile.TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "session.json"
        saved_path = session.save(path)
        loaded = Session.load(saved_path)

        # For text-only turns, save/load should behave like a public round-trip
        # with no semantic loss in system prompt or transcript history.
        assert loaded.system == session.system
        assert loaded.history == session.history


@given(system=_OPTIONAL_SYSTEM, turns=st.lists(_TEXT_ONLY_TURN, max_size=5))
@settings(deadline=None)
def test_save_load_then_fork_still_produces_independent_future_branches(
    *,
    system: str | None,
    turns: list[tuple[_USER_CONTENT, str, dict[str, object]]],
) -> None:
    """A loaded session should still support normal future branch semantics."""
    session = Session(system=system)
    _apply_turns(session, turns)

    with tempfile.TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "session.json"
        loaded = Session.load(session.save(path))
        forked = loaded.fork()

        loaded.remember(user_content="left", assistant_text="left", assistant_meta={})
        forked.remember(
            user_content="right",
            assistant_text="right",
            assistant_meta={},
        )

        # Persistence should not collapse future branch independence. Once the
        # session is loaded back, later branches should still diverge normally.
        assert loaded.history != forked.history
        assert loaded.history[-2].parts == ("left",)
        assert forked.history[-2].parts == ("right",)


@given(
    system=_OPTIONAL_SYSTEM,
    leading_text=st.one_of(st.none(), _NONEMPTY_TEXT),
    middle_text=_TEXT,
    assistant_text=_TEXT,
    assistant_meta=_ASSISTANT_META,
    file_name=_SAFE_NAME,
    file_data=st.binary(max_size=32),
    video_name=_SAFE_NAME,
    video_data=st.binary(max_size=48),
    host=_SAFE_NAME,
    fps=st.integers(min_value=1, max_value=5),
    start_offset=st.one_of(st.none(), st.integers(min_value=0, max_value=20)),
    end_offset=st.one_of(st.none(), st.integers(min_value=0, max_value=20)),
)
@settings(max_examples=20, deadline=None)
def test_save_load_preserves_multimodal_public_transcript_meaning(
    *,
    system: str | None,
    leading_text: str | None,
    middle_text: str,
    assistant_text: str,
    assistant_meta: dict[str, object],
    file_name: str,
    file_data: bytes,
    video_name: str,
    video_data: bytes,
    host: str,
    fps: int,
    start_offset: int | None,
    end_offset: int | None,
) -> None:
    """Save/load should preserve multimodal transcript meaning across reload."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        content = _build_multimodal_content(
            temp_dir=temp_path,
            leading_text=leading_text,
            middle_text=middle_text,
            file_name=file_name,
            file_data=file_data,
            video_name=video_name,
            video_data=video_data,
            host=host,
            fps=fps,
            start_offset=start_offset,
            end_offset=end_offset,
        )
        session = Session(system=system)
        session.remember(
            user_content=content,
            assistant_text=assistant_text,
            assistant_meta=assistant_meta,
        )
        before = _normalize_parts(session.build_messages(content, include_history=True))

        loaded = Session.load(session.save(temp_path / "session.json"))
        after = _normalize_parts(loaded.build_messages(content, include_history=True))

        # File/video materialization paths may change across reload, so this
        # property compares the public meaning of the transcript: ordering,
        # media kind, persisted bytes, and assistant metadata.
        assert loaded.system == session.system
        assert after == before
        assert len(loaded.history) == len(session.history)
        assert _normalize_parts(loaded.history[0].parts) == _normalize_parts(
            session.history[0].parts
        )
        assert loaded.history[1].parts == (assistant_text,)
        assert loaded.history[1].meta == assistant_meta

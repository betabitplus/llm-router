from __future__ import annotations

import tempfile
from pathlib import Path

from hypothesis import given, settings, strategies as st

from llm_router._internal.session import SessionStore

_TEXT = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789 _-",
    max_size=24,
)
_META = st.dictionaries(
    keys=st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz0123456789_-",
        min_size=1,
        max_size=12,
    ),
    values=st.one_of(_TEXT, st.integers(min_value=0, max_value=20), st.booleans()),
    max_size=3,
)
_TURN = st.tuples(_TEXT, _TEXT, _META)


@given(turns=st.lists(_TURN, max_size=8))
def test_arbitrary_text_turns_remain_alternating_history(
    turns: list[tuple[str, str, dict[str, object]]],
) -> None:
    store = SessionStore()

    for user_text, assistant_text, meta in turns:
        store.remember(
            user_content=user_text,
            assistant_text=assistant_text,
            assistant_meta=meta,
        )

    assert [message.role for message in store.history] == [
        role for _turn in turns for role in ("user", "assistant")
    ]


@given(turns=st.lists(_TURN, max_size=5), left=_TURN, right=_TURN)
def test_forked_branches_diverge_independently(
    turns: list[tuple[str, str, dict[str, object]]],
    left: tuple[str, str, dict[str, object]],
    right: tuple[str, str, dict[str, object]],
) -> None:
    store = SessionStore()
    for user_text, assistant_text, meta in turns:
        store.remember(
            user_content=user_text,
            assistant_text=assistant_text,
            assistant_meta=meta,
        )
    forked = store.fork()

    store.remember(user_content=left[0], assistant_text=left[1], assistant_meta=left[2])
    forked.remember(
        user_content=right[0],
        assistant_text=right[1],
        assistant_meta=right[2],
    )

    assert store.history[: len(turns) * 2] == forked.history[: len(turns) * 2]
    assert store.history[-2].parts == (left[0],)
    assert forked.history[-2].parts == (right[0],)


@given(turns=st.lists(_TURN, max_size=5))
@settings(deadline=None)
def test_save_load_preserves_text_turn_metadata(
    turns: list[tuple[str, str, dict[str, object]]],
) -> None:
    store = SessionStore(system="system")
    for user_text, assistant_text, meta in turns:
        store.remember(
            user_content=user_text,
            assistant_text=assistant_text,
            assistant_meta=meta,
        )

    with tempfile.TemporaryDirectory() as temp_dir:
        loaded = SessionStore.load(store.save(Path(temp_dir) / "session.json"))

    assert loaded.system == store.system
    assert loaded.history == store.history

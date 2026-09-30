# mutation-pin: TREQ_SESSION_SERIALIZATION f1db3a48e54f5fe2
# pinned-by: claude-opus-5-5
from __future__ import annotations

import json

import pytest

from llm_router._api.types import ChatMessage
from llm_router._internal.session.serialization import decode_session

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_SESSION_SERIALIZATION[revision==1]")
def test_decoded_history_is_a_stable_tuple_of_saved_messages() -> None:
    text = json.dumps(
        {
            "version": 1,
            "system": "Be brief.",
            "history": [
                {"role": "user", "parts": [], "meta": {}},
                {"role": "assistant", "parts": [], "meta": {"note": "first"}},
            ],
        }
    )
    expected = (
        ChatMessage(role="user", parts=(), meta={}),
        ChatMessage(role="assistant", parts=(), meta={"note": "first"}),
    )

    system, history = decode_session(text)

    assert system == "Be brief."
    assert isinstance(history, tuple)
    assert history == expected
    # Reading the same history again must give the same content.
    assert history == expected
    assert len(history) == 2

    again_system, again_history = decode_session(text)
    assert again_system == system
    assert isinstance(again_history, tuple)
    assert again_history == history


@pytest.mark.verifies("TREQ_SESSION_SERIALIZATION[revision==1]")
def test_decoded_empty_history_is_an_empty_tuple() -> None:
    system, history = decode_session('{"version": 1, "history": []}')

    assert system is None
    assert isinstance(history, tuple)
    assert history == ()

# mutation-pin: TREQ_SESSION_SERIALIZATION FN-039B7B95
# pinned-by: delegate, one pin for 2 pins of encode_session
# kills: 00e231387191a730 SM-B91A9265
from __future__ import annotations

import pytest

from llm_router._api.types import ChatMessage
from llm_router._internal.session.serialization import decode_session, encode_session

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_SESSION_SERIALIZATION[revision==1]")
def test_session_roundtrip_keeps_system_and_repeated_messages() -> None:
    message = ChatMessage(role="user", parts=(), meta={})
    history = (message, message, message)
    system_prompt = 'You are "helpful".\nUse a \\ backslash.'

    artifact = encode_session(system=system_prompt, history=history)
    system, loaded = decode_session(artifact)

    assert system == system_prompt
    assert len(loaded) == len(history)
    assert [item.role for item in loaded] == [item.role for item in history]
    assert [tuple(item.parts) for item in loaded] == [
        tuple(item.parts) for item in history
    ]
    assert [item.meta for item in loaded] == [item.meta for item in history]

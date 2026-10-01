# mutation-pin: TREQ_SESSION_SERIALIZATION SM-B91A9265
# pinned-by: claude-opus-5-5
from __future__ import annotations

import json

import pytest

from llm_router._api.types import ChatMessage
from llm_router._internal.session.serialization import encode_session

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_SESSION_SERIALIZATION[revision==1]")
def test_encode_session_keeps_repeated_identical_messages() -> None:
    message = ChatMessage(role="user", parts=(), meta={})
    history = (message, message, message)

    artifact = encode_session(system=None, history=history)
    payload = json.loads(artifact)

    assert len(payload["history"]) == len(history)
    for encoded in payload["history"]:
        assert encoded["role"] == "user"
        assert encoded["parts"] == []

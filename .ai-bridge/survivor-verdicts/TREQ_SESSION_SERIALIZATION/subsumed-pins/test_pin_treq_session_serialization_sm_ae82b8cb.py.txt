# mutation-pin: TREQ_SESSION_SERIALIZATION SM-AE82B8CB
# pinned-by: claude-opus-5-5
from __future__ import annotations

import json

import pytest

from llm_router._internal.session import SessionStore
from llm_router._internal.session.serialization import encode_session

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_SESSION_SERIALIZATION[revision==1]")
def test_encode_session_keeps_every_history_message() -> None:
    store = SessionStore(system="be brief")
    store.remember("first question", "first answer")
    store.remember("second question", "second answer")

    history = store.history
    assert len(history) == 4

    text = encode_session(system=store.system, history=history)
    payload = json.loads(text)

    assert payload["system"] == "be brief"
    assert len(payload["history"]) == len(history)
    assert "second answer" in text

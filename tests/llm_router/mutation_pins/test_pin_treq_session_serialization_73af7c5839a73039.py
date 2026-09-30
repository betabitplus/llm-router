# mutation-pin: TREQ_SESSION_SERIALIZATION 73af7c5839a73039
# pinned-by: claude-opus-5-5
from __future__ import annotations

import json

import pytest

from llm_router._internal.session.serialization import decode_session

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_SESSION_SERIALIZATION[revision==1]")
def test_decode_session_preserves_string_system_prompt() -> None:
    prompt = "You are a concise assistant."
    text = json.dumps({"version": 1, "system": prompt, "history": []})

    system, history = decode_session(text)

    assert system == prompt
    assert history == ()

# mutation-pin: TREQ_SESSION_SERIALIZATION 00e231387191a730
# pinned-by: claude-opus-5-5
from __future__ import annotations

import json

import pytest

from llm_router._internal.session.serialization import encode_session

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_SESSION_SERIALIZATION[revision==1]")
def test_encode_session_keeps_system_prompt() -> None:
    system_prompt = 'You are "helpful".\nUse a \\ backslash.'

    artifact = encode_session(system=system_prompt, history=())
    payload = json.loads(artifact)

    assert payload["system"] == system_prompt
    assert payload["history"] == []

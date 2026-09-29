# semantic-mutant: SM-A96F2E5C
from __future__ import annotations

import json

import pytest

from llm_router._internal.session.serialization import encode_session

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_SESSION_SERIALIZATION[revision==1]")
def test_encode_session_preserves_empty_system_string() -> None:
    text = encode_session(system="", history=())

    payload = json.loads(text)

    assert payload["system"] == ""
    assert payload["history"] == []
    assert payload["version"] == 1

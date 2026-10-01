# mutation-pin: TREQ_SESSION_SERIALIZATION 84e67158176fdd1f
# pinned-by: claude-opus-5-5
from __future__ import annotations

import json

import pytest

from llm_router._internal.runtime.errors import SessionSerializationError
from llm_router._internal.session.serialization import decode_session

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_SESSION_SERIALIZATION[revision==1]")
@pytest.mark.parametrize("system", [123, ["be brief"], {"text": "hi"}, True])
def test_decode_rejects_non_string_system_prompt(system: object) -> None:
    text = json.dumps({"version": 1, "system": system, "history": []})

    with pytest.raises(SessionSerializationError, match=r"system prompt"):
        decode_session(text)

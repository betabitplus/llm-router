# mutation-pin: TREQ_SESSION_SERIALIZATION 5eca933c7a02d62f
# pinned-by: claude-opus-5-5
from __future__ import annotations

import json

import pytest

from llm_router._internal.runtime.errors import SessionSerializationError
from llm_router._internal.session.serialization import decode_session

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_SESSION_SERIALIZATION[revision==1]")
@pytest.mark.parametrize(
    "payload",
    [
        {"version": 1, "system": "be brief"},
        {"version": 1, "system": None, "history": ""},
        {"version": 1, "system": None, "history": {}},
    ],
)
def test_decode_rejects_missing_or_empty_non_list_history(
    payload: dict[str, object],
) -> None:
    text = json.dumps(payload)

    with pytest.raises(SessionSerializationError, match=r"history must be a list"):
        decode_session(text)

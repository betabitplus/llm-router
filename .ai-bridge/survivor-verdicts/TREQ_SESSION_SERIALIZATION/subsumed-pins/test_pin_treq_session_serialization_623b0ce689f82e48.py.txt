# mutation-pin: TREQ_SESSION_SERIALIZATION 623b0ce689f82e48
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router._internal.runtime.errors import SessionSerializationError
from llm_router._internal.session.serialization import decode_session

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_SESSION_SERIALIZATION[revision==1]")
@pytest.mark.parametrize(
    "text",
    ["1", "[]", '"hello"', "null", "true", "[1, 2]\n", "42\r", "3.5"],
    ids=[
        "int",
        "empty-list",
        "string",
        "null",
        "bool",
        "list-newline",
        "int-cr",
        "float",
    ],
)
def test_decode_rejects_non_object_json(text: str) -> None:
    with pytest.raises(SessionSerializationError, match=r"must be a JSON object"):
        decode_session(text)

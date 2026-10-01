# mutation-pin: TREQ_SESSION_SERIALIZATION 5e426e56bd7decaf
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router._internal.runtime.errors import SessionSerializationError
from llm_router._internal.session.serialization import decode_session

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_SESSION_SERIALIZATION[revision==1]")
@pytest.mark.parametrize(
    "text",
    ["[]", "42", "null", '"text"', "[1, 2]", "true"],
    ids=["empty-list", "number", "null", "string", "list", "bool"],
)
def test_decode_session_rejects_non_object_json_with_serialization_error(
    text: str,
) -> None:
    with pytest.raises(SessionSerializationError, match=r"must be a JSON object"):
        decode_session(text)

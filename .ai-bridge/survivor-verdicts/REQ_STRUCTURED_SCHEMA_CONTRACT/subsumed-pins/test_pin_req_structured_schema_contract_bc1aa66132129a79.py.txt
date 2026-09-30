# mutation-pin: REQ_STRUCTURED_SCHEMA_CONTRACT bc1aa66132129a79
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router._internal.capabilities.schema import normalize_schema

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_normalize_schema_rejects_non_object_mapping() -> None:
    schema = {
        "title": "Reply",
        "type": "string",
        "description": "Single string message.",
    }
    with pytest.raises(
        ValueError,
        match=r"response_schema mapping must describe a JSON object\.",
    ):
        normalize_schema(schema)

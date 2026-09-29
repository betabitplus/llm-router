# mutation-pin: REQ_STRUCTURED_SCHEMA_CONTRACT 4b031c8b4a869092
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router._internal.capabilities.schema import normalize_schema

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_mapping_schema_name_resolution() -> None:
    titled_spec = normalize_schema(
        {
            "title": "Reply",
            "type": "object",
            "properties": {"answer": {"type": "string"}},
        }
    )
    assert titled_spec.name == "Reply"

    id_spec = normalize_schema(
        {
            "$id": "https://example.com/reply.json",
            "type": "object",
            "properties": {"answer": {"type": "string"}},
        }
    )
    assert id_spec.name == "https://example.com/reply.json"

    fallback_spec = normalize_schema(
        {
            "type": "object",
            "properties": {"answer": {"type": "string"}},
        }
    )
    assert fallback_spec.name == "structured_response"

# mutation-pin: REQ_STRUCTURED_SCHEMA_CONTRACT SM-9C5C73BC
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router._internal.capabilities.schema import normalize_schema

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_mapping_schema_is_isolated_from_caller_mutation() -> None:
    schema = {
        "type": "object",
        "properties": {"a": {"type": "integer"}},
        "required": ["a"],
    }

    spec = normalize_schema(schema)
    schema["properties"]["a"]["type"] = "string"

    assert spec.json_schema["properties"]["a"]["type"] == "integer"
    assert spec.parse('{"a": 1}') == {"a": 1}
    with pytest.raises(Exception, match=r"string|integer|is not of type"):
        spec.parse('{"a": "x"}')

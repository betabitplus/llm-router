# mutation-pin: REQ_STRUCTURED_SCHEMA_CONTRACT SM-6B29FD70
# pinned-by: claude-opus-5-5
from __future__ import annotations

import json

import pytest

from llm_router._internal.capabilities.schema import normalize_schema

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_mapping_parser_enforces_constraints_from_defs_ref() -> None:
    schema = {
        "type": "object",
        "properties": {"item": {"$ref": "#/$defs/Item"}},
        "required": ["item"],
        "$defs": {
            "Item": {
                "type": "object",
                "properties": {"quantity": {"type": "integer", "minimum": 1}},
                "required": ["quantity"],
            }
        },
    }

    spec = normalize_schema(schema)

    assert "$defs" in spec.json_schema
    good = spec.parse(json.dumps({"item": {"quantity": 3}}))
    assert good == {"item": {"quantity": 3}}
    with pytest.raises(Exception, match=r"less than the minimum of 1"):
        spec.parse(json.dumps({"item": {"quantity": 0}}))

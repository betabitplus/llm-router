# mutation-pin: REQ_STRUCTURED_SCHEMA_CONTRACT SM-2093BBD0
# pinned-by: claude-opus-5-5
from __future__ import annotations

from typing import Any

import pytest

from llm_router._internal.capabilities.schema import (
    SchemaSpec,
    with_schema_transform,
)

pytestmark = pytest.mark.verification_kind("unit")


def parse_payload(value: object) -> object:
    return value


def identity(json_schema: Any) -> Any:
    return dict(json_schema)


def make_spec() -> SchemaSpec:
    json_schema = {
        "type": "object",
        "properties": {"item": {"$ref": "#/$defs/Item"}},
        "required": ["item"],
        "$defs": {
            "Item": {
                "type": "object",
                "properties": {"count": {"type": "integer", "minimum": 1}},
                "required": ["count"],
            }
        },
    }
    return SchemaSpec(
        name="nested_spec",
        json_schema=json_schema,
        parser=parse_payload,
    )


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_with_schema_transform_keeps_defs_for_nested_refs() -> None:
    spec = make_spec()

    result = with_schema_transform(spec, identity)

    assert "$defs" in result.json_schema
    assert result.json_schema["$defs"] == spec.json_schema["$defs"]
    assert result.json_schema["properties"]["item"] == {"$ref": "#/$defs/Item"}
    item = result.json_schema["$defs"]["Item"]
    assert item["properties"]["count"]["minimum"] == 1

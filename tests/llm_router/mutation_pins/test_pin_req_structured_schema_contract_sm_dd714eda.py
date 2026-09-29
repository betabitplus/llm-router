# mutation-pin: REQ_STRUCTURED_SCHEMA_CONTRACT SM-DD714EDA
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
    return json_schema


def make_spec() -> SchemaSpec:
    json_schema = {
        "type": "object",
        "$defs": {
            "level": {"type": "string", "enum": ["low", "high"]},
        },
        "properties": {"level": {"$ref": "#/$defs/level"}},
        "required": ["level"],
        "minProperties": 1,
        "allOf": [{"required": ["level"]}],
    }
    return SchemaSpec(
        name="level_spec",
        json_schema=json_schema,
        parser=parse_payload,
    )


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_with_schema_transform_keeps_nested_constraints() -> None:
    spec = make_spec()

    result = with_schema_transform(spec, identity)

    for key in ("$defs", "minProperties", "allOf"):
        assert key in result.json_schema
    assert result.json_schema["$defs"] == spec.json_schema["$defs"]
    assert result.json_schema["allOf"] == spec.json_schema["allOf"]
    assert result.json_schema["minProperties"] == 1
    assert dict(result.json_schema) == dict(spec.json_schema)
    assert result.name == "level_spec"

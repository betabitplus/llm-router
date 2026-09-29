# mutation-pin: REQ_STRUCTURED_SCHEMA_CONTRACT 24bb2ffb3a209650
# pinned-by: claude-opus-5-5
from __future__ import annotations

from typing import Any

import pytest

from llm_router._internal.capabilities.schema import SchemaSpec, with_schema_transform

pytestmark = pytest.mark.verification_kind("unit")


def parse_payload(value: object) -> object:
    assert isinstance(value, dict)
    assert isinstance(value["count"], int)
    return value


def add_additional_properties_false(json_schema: Any) -> Any:
    return {**json_schema, "additionalProperties": False}


def make_spec() -> SchemaSpec:
    json_schema = {
        "type": "object",
        "properties": {"count": {"type": "integer", "minimum": 0}},
        "required": ["count"],
    }
    return SchemaSpec(
        name="original_spec_name",
        json_schema=json_schema,
        parser=parse_payload,
    )


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_with_schema_transform_keeps_name_when_none_given() -> None:
    spec = make_spec()

    result = with_schema_transform(spec, add_additional_properties_false)

    assert result.name == "original_spec_name"
    assert result.json_schema["additionalProperties"] is False


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_with_schema_transform_replaces_name_when_given() -> None:
    spec = make_spec()

    result = with_schema_transform(
        spec, add_additional_properties_false, name="renamed_spec"
    )

    assert result.name == "renamed_spec"


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_with_schema_transform_preserves_router_side_validation() -> None:
    spec = make_spec()

    result = with_schema_transform(spec, add_additional_properties_false)

    assert result.parse({"count": 2}) == {"count": 2}

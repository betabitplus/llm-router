# mutation-pin: REQ_STRUCTURED_SCHEMA_CONTRACT c8e877b2ede451a3
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router._internal.capabilities.schema import SchemaSpec, with_schema_transform

pytestmark = pytest.mark.verification_kind("unit")


def parse_ticket(value: object) -> object:
    return value


def add_additional_properties_false(
    schema: dict[str, object],
) -> dict[str, object]:
    updated = dict(schema)
    updated["additionalProperties"] = False
    return updated


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_with_schema_transform_applies_output_and_keeps_or_sets_name() -> None:
    original_schema = {
        "type": "object",
        "properties": {
            "priority": {"type": "integer", "minimum": 1, "maximum": 5},
        },
        "required": ["priority"],
    }
    spec = SchemaSpec(
        name="ticket_schema",
        json_schema=original_schema,
        parser=parse_ticket,
    )

    overridden = with_schema_transform(
        spec, add_additional_properties_false, name="strict_ticket_schema"
    )

    expected_schema = add_additional_properties_false(original_schema)
    assert overridden.json_schema == expected_schema
    assert overridden.json_schema != original_schema
    assert overridden.name == "strict_ticket_schema"

    kept_name = with_schema_transform(spec, add_additional_properties_false)
    assert kept_name.name == "ticket_schema"
    assert kept_name.json_schema == expected_schema

    nested_properties = overridden.json_schema["properties"]
    priority_constraints = nested_properties["priority"]
    assert overridden.json_schema["required"] == ["priority"]
    assert priority_constraints["minimum"] == 1
    assert priority_constraints["maximum"] == 5
    assert overridden.json_schema["additionalProperties"] is False

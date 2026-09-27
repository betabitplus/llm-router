# mutation-pin: TREQ_REPAIR_PROMPT_BOUNDS 9341379044dfc2f2
# pinned-by: claude-opus-5-5
from __future__ import annotations

import json

import pytest
from hypothesis import given, settings, strategies as st

from llm_router._internal.capabilities.schema import (
    SchemaSpec,
    build_repair_prompt,
    normalize_schema,
    preview_text,
    preview_value,
)

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_REPAIR_PROMPT_BOUNDS[revision==2]")
def test_repair_prompt_contains_dynamic_components_for_short_inputs() -> None:
    schema = {
        "type": "object",
        "properties": {
            "user_id": {"type": "integer"},
            "username": {"type": "string"},
        },
        "required": ["user_id", "username"],
    }
    spec = SchemaSpec(name="UserProfile", json_schema=schema, parser=None)
    invalid_output = '{"user_id": "not_an_int", "username": "alice"}'
    error_message = "Value error, expected integer for user_id"

    prompt = build_repair_prompt(
        spec=spec,
        invalid_output=invalid_output,
        error_message=error_message,
    )

    expected_schema_preview = json.dumps(dict(spec.json_schema), sort_keys=True)

    assert "The previous response did not match the required schema." in prompt
    assert f"Schema: {spec.name}" in prompt
    assert f"Required schema preview: {expected_schema_preview}" in prompt
    assert f"Validation error: {error_message}" in prompt
    assert f"Previous response preview: {invalid_output}" in prompt
    assert "Return only valid JSON that satisfies the schema." in prompt


@pytest.mark.verifies("TREQ_REPAIR_PROMPT_BOUNDS[revision==2]")
@given(
    schema_name=st.text(
        alphabet=st.characters(whitelist_categories=("L", "N")),
        min_size=200,
        max_size=1_000,
    ),
    invalid_output=st.text(
        alphabet=st.characters(whitelist_categories=("L", "N")),
        min_size=600,
        max_size=1_500,
    ),
    error_message=st.text(
        alphabet=st.characters(whitelist_categories=("L", "N")),
        min_size=400,
        max_size=1_000,
    ),
)
@settings(max_examples=50)
def test_repair_prompt_bounds_and_contains_truncated_components_for_oversized_inputs(
    *,
    schema_name: str,
    invalid_output: str,
    error_message: str,
) -> None:
    spec = normalize_schema({"title": schema_name, "type": "object"})
    prompt = build_repair_prompt(
        spec=spec,
        invalid_output=invalid_output,
        error_message=error_message,
    )

    assert len(prompt) <= 1_200

    expected_schema_name = preview_text(spec.name, max_chars=120)
    expected_schema_preview = preview_text(
        json.dumps(dict(spec.json_schema), sort_keys=True),
        max_chars=500,
    )
    expected_error_preview = preview_text(error_message, max_chars=300)
    expected_output_preview = preview_value(invalid_output, max_chars=500)

    assert expected_schema_name in prompt
    assert expected_schema_preview in prompt
    assert expected_error_preview in prompt
    assert expected_output_preview in prompt

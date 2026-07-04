from __future__ import annotations

import pytest
from pydantic import BaseModel

from llm_router._internal.capabilities.schema import (
    SchemaRepairState,
    advance_repair_attempt,
    build_repair_prompt,
    normalize_schema,
    validate_schema_output,
    with_schema_transform,
)


class Answer(BaseModel):
    answer: int


def test_pydantic_schema_parses_json_into_model() -> None:
    spec = normalize_schema(Answer)

    result = validate_schema_output(spec, '{"answer": 3}')

    assert spec.name == "Answer"
    assert result.valid is True
    assert result.value == Answer(answer=3)


def test_pydantic_schema_reports_validation_failure_safely() -> None:
    spec = normalize_schema(Answer)

    result = validate_schema_output(spec, '{"answer": "nope"}')

    assert result.valid is False
    assert result.error_message is not None
    assert "answer" in result.error_message


def test_mapping_schema_validates_required_fields_and_types() -> None:
    spec = normalize_schema(
        {
            "title": "Reply",
            "type": "object",
            "required": ["answer"],
            "properties": {"answer": {"type": "string"}},
        }
    )

    assert validate_schema_output(spec, {"answer": "ok"}).valid is True
    missing = validate_schema_output(spec, {})
    wrong_type = validate_schema_output(spec, {"answer": 1})

    assert missing.valid is False
    assert "Missing required field" in str(missing.error_message)
    assert wrong_type.valid is False
    assert "expected type" in str(wrong_type.error_message)


def test_mapping_schema_validates_common_string_and_array_constraints() -> None:
    spec = normalize_schema(
        {
            "title": "Reply",
            "type": "object",
            "required": ["severity", "tags"],
            "properties": {
                "severity": {"type": "string", "minLength": 3},
                "tags": {"type": "array", "minItems": 1},
            },
        }
    )

    short = validate_schema_output(spec, {"severity": "ok", "tags": ["x"]})
    empty = validate_schema_output(spec, {"severity": "high", "tags": []})
    valid = validate_schema_output(spec, {"severity": "high", "tags": ["x"]})

    assert short.valid is False
    assert "minLength" in str(short.error_message)
    assert empty.valid is False
    assert "minItems" in str(empty.error_message)
    assert valid.valid is True


def test_mapping_schema_accepts_fenced_json_text() -> None:
    spec = normalize_schema(
        {
            "title": "Reply",
            "type": "object",
            "required": ["answer"],
            "properties": {"answer": {"type": "string"}},
        }
    )

    result = validate_schema_output(spec, '```json\n{"answer": "ok"}\n```')

    assert result.valid is True
    assert result.value == {"answer": "ok"}


def test_repair_prompt_uses_bounded_error_and_output_previews() -> None:
    spec = normalize_schema(
        {
            "title": "Reply",
            "type": "object",
            "required": ["severity"],
            "properties": {"severity": {"type": "string", "minLength": 3}},
        }
    )

    prompt = build_repair_prompt(
        spec=spec,
        invalid_output={"bad": "x" * 1_000},
        error_message="field failed " * 100,
    )

    assert "Schema: Reply" in prompt
    assert "required" in prompt
    assert "minLength" in prompt
    assert "Return only valid JSON" in prompt
    assert len(prompt) < 1_700


def test_schema_transform_hook_returns_transformed_copy() -> None:
    spec = normalize_schema(
        {
            "title": "Reply",
            "$ref": "#/$defs/Reply",
            "$defs": {"Reply": {"type": "object"}},
        }
    )

    transformed = with_schema_transform(
        spec,
        lambda schema: {"title": schema["title"], "type": "object"},
        name="AistudioReply",
    )

    assert transformed.name == "AistudioReply"
    assert "$ref" not in transformed.json_schema
    assert "$ref" in spec.json_schema


def test_repair_state_tracks_attempt_capacity() -> None:
    state = SchemaRepairState(max_attempts=2)

    first = advance_repair_attempt(state)
    second = advance_repair_attempt(first)

    assert state.can_attempt_repair() is True
    assert first.can_attempt_repair() is True
    assert second.can_attempt_repair() is False


def test_invalid_repair_state_fails() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        SchemaRepairState(max_attempts=0)

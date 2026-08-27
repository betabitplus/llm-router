from __future__ import annotations

from pydantic import BaseModel

from llm_router._internal.capabilities.schema import (
    normalize_schema,
    validate_schema_output,
)


class Answer(BaseModel):
    answer: int


def test_pydantic_schema_parses_json_into_model() -> None:
    result = validate_schema_output(normalize_schema(Answer), '{"answer": 3}')

    assert result.valid is True
    assert result.value == Answer(answer=3)


def test_mapping_schema_enforces_required_types_and_common_constraints() -> None:
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

    assert validate_schema_output(spec, {"severity": "high", "tags": ["x"]}).valid
    assert not validate_schema_output(spec, {"tags": ["x"]}).valid
    assert not validate_schema_output(spec, {"severity": 7, "tags": ["x"]}).valid
    assert not validate_schema_output(spec, {"severity": "ok", "tags": ["x"]}).valid
    assert not validate_schema_output(spec, {"severity": "high", "tags": []}).valid


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

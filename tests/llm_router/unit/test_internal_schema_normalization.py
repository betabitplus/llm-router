from __future__ import annotations

import pytest
from pydantic import BaseModel

from llm_router._internal.capabilities.schema import (
    normalize_schema,
    validate_schema_output,
)

pytestmark = [
    pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]"),
    pytest.mark.verification_kind("unit"),
]


class Answer(BaseModel):
    answer: int


@pytest.mark.coverage_item("VC_SCHEMA_PYDANTIC_RECONSTRUCTION")
def test_pydantic_schema_preserves_contract_and_reconstructs_requested_model() -> None:
    spec = normalize_schema(Answer)
    result = validate_schema_output(spec, '{"answer": 3}')

    assert spec.model_type is Answer
    assert dict(spec.json_schema) == Answer.model_json_schema()
    assert result.valid is True
    assert result.value == Answer(answer=3)


@pytest.mark.coverage_item("VC_SCHEMA_MAPPING_ENFORCEMENT")
def test_mapping_schema_enforces_draft_2020_12_nested_constraints() -> None:
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Incident",
        "type": "object",
        "required": ["incident_id", "severity", "service"],
        "additionalProperties": False,
        "properties": {
            "incident_id": {
                "type": "string",
                "pattern": r"^INC-\d{4}$",
            },
            "severity": {
                "type": "string",
                "enum": ["SEV1", "SEV2", "SEV3"],
            },
            "service": {
                "type": "object",
                "required": ["name", "ports"],
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string", "minLength": 3},
                    "ports": {
                        "type": "array",
                        "minItems": 1,
                        "uniqueItems": True,
                        "items": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 65535,
                        },
                    },
                },
            },
        },
    }
    spec = normalize_schema(schema)
    valid = {
        "incident_id": "INC-1042",
        "severity": "SEV2",
        "service": {"name": "api", "ports": [443, 8443]},
    }

    assert dict(spec.json_schema) == schema
    assert validate_schema_output(spec, valid).valid is True

    invalid_payloads = (
        {**valid, "incident_id": "incident-1042"},
        {**valid, "severity": "SEV9"},
        {**valid, "unexpected": True},
        {**valid, "service": {"name": "api", "ports": []}},
        {**valid, "service": {"name": "api", "ports": [443, 443]}},
        {**valid, "service": {"name": "api", "ports": [70000]}},
    )
    assert all(
        not validate_schema_output(spec, payload).valid for payload in invalid_payloads
    )


@pytest.mark.coverage_item("VC_SCHEMA_INVALID_MAPPING_REJECTION")
def test_invalid_mapping_schema_is_rejected_during_normalization() -> None:
    invalid_schema = {
        "type": "object",
        "properties": {
            "answer": {
                "type": "definitely-not-a-json-schema-type",
            },
        },
    }

    with pytest.raises(ValueError, match="valid Draft 2020-12 JSON Schema"):
        normalize_schema(invalid_schema)


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

"""Structured-output schema normalization.

Why:
    Owns provider-neutral schema validation and repair-loop decisions before
    adapter-specific schema translation happens at the edge.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from copy import deepcopy
from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Any

from py_lib_runtime import preview_text, preview_value
from pydantic import BaseModel

_MIN_FENCED_JSON_LINES = 2


@dataclass(frozen=True, slots=True)
class SchemaSpec:
    """Provider-neutral structured-output schema."""

    name: str
    json_schema: Mapping[str, Any]
    parser: Callable[[object], object]
    model_type: type[BaseModel] | None = None

    def __post_init__(self) -> None:
        """Freeze the top-level schema mapping after construction."""
        object.__setattr__(
            self,
            "json_schema",
            MappingProxyType(deepcopy(dict(self.json_schema))),
        )

    def parse(self, value: object) -> object:
        """Parse and validate a candidate structured output."""
        return self.parser(value)


@dataclass(frozen=True, slots=True)
class SchemaValidationResult:
    """Result of validating one structured-output candidate."""

    valid: bool
    value: object | None = None
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class SchemaRepairState:
    """Structured-output repair-loop state."""

    max_attempts: int
    completed_attempts: int = 0

    def __post_init__(self) -> None:
        """Validate repair counter bounds."""
        if self.max_attempts < 1:
            msg = "schema repair max attempts must be at least 1."
            raise ValueError(msg)
        if self.completed_attempts < 0:
            msg = "schema repair completed attempts cannot be negative."
            raise ValueError(msg)

    def can_attempt_repair(self) -> bool:
        """Return whether another repair prompt may be attempted."""
        return self.completed_attempts < self.max_attempts


def advance_repair_attempt(state: SchemaRepairState) -> SchemaRepairState:
    """Return repair state after one attempted repair turn."""
    return SchemaRepairState(
        max_attempts=state.max_attempts,
        completed_attempts=state.completed_attempts + 1,
    )


def normalize_schema(schema: object) -> SchemaSpec:
    """Convert a public schema input into a provider-neutral schema spec."""
    if isinstance(schema, type) and issubclass(schema, BaseModel):
        return _pydantic_schema_spec(schema)
    if isinstance(schema, Mapping):
        copied = deepcopy(dict(schema))
        name = str(copied.get("title") or copied.get("$id") or "structured_response")
        return SchemaSpec(
            name=name,
            json_schema=copied,
            parser=lambda value: _parse_mapping_schema(copied, value),
        )

    msg = "response_schema must be a Pydantic model type or JSON schema mapping."
    raise TypeError(msg)


def validate_schema_output(
    spec: SchemaSpec,
    value: object,
) -> SchemaValidationResult:
    """Validate a candidate structured output without raising."""
    try:
        parsed = spec.parse(value)
    except Exception as exc:
        return SchemaValidationResult(
            valid=False,
            error_message=preview_value(exc),
        )
    return SchemaValidationResult(valid=True, value=parsed)


def build_repair_prompt(
    *,
    spec: SchemaSpec,
    invalid_output: object,
    error_message: str,
) -> str:
    """Build bounded validation guidance for a structured-output repair turn."""
    output_preview = preview_value(invalid_output, max_chars=500)
    error_preview = preview_text(error_message, max_chars=300)
    schema_preview = preview_text(
        json.dumps(dict(spec.json_schema), sort_keys=True),
        max_chars=500,
    )
    return (
        "The previous response did not match the required schema.\n"
        f"Schema: {spec.name}\n"
        f"Required schema preview: {schema_preview}\n"
        f"Validation error: {error_preview}\n"
        f"Previous response preview: {output_preview}\n"
        "Return only valid JSON that satisfies the schema."
    )


def with_schema_transform(
    spec: SchemaSpec,
    transform: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    *,
    name: str | None = None,
) -> SchemaSpec:
    """Return a copy of `spec` with an adapter-provided schema transform."""
    transformed = transform(spec.json_schema)
    return replace(
        spec,
        name=spec.name if name is None else name,
        json_schema=transformed,
    )


def _pydantic_schema_spec(model: type[BaseModel]) -> SchemaSpec:
    """Return a schema spec backed by Pydantic validation."""
    return SchemaSpec(
        name=model.__name__,
        json_schema=model.model_json_schema(),
        parser=lambda value: _parse_pydantic_model(model, value),
        model_type=model,
    )


def _parse_pydantic_model(model: type[BaseModel], value: object) -> BaseModel:
    """Parse a Pydantic model from text, mappings, or existing model objects."""
    if isinstance(value, model):
        return value
    if isinstance(value, str):
        payload = _extract_json_payload(value)
        return model.model_validate_json(payload)
    return model.model_validate(value)


def _parse_mapping_schema(schema: Mapping[str, Any], value: object) -> dict[str, Any]:
    """Parse and lightly validate output against a JSON schema mapping."""
    parsed = _parse_json_object(value)
    _validate_mapping_schema(schema, parsed)
    return parsed


def _parse_json_object(value: object) -> dict[str, Any]:
    """Parse a structured-output candidate into a JSON object mapping."""
    if isinstance(value, str):
        value = _extract_json_payload(value)
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError as exc:
            msg = f"Structured output is not valid JSON: {exc.msg}."
            raise ValueError(msg) from exc
    else:
        decoded = value

    if not isinstance(decoded, dict):
        msg = "Structured output must be a JSON object."
        raise TypeError(msg)
    return {str(key): item for key, item in decoded.items()}


def _validate_mapping_schema(
    schema: Mapping[str, Any],
    value: Mapping[str, Any],
) -> None:
    """Validate a small provider-neutral subset of JSON Schema."""
    schema_type = schema.get("type")
    if schema_type not in {None, "object"}:
        msg = "Only object JSON schemas are supported by provider-neutral validation."
        raise ValueError(msg)

    required = schema.get("required", ())
    if isinstance(required, list | tuple):
        for field_name in required:
            if isinstance(field_name, str) and field_name not in value:
                msg = f"Missing required field: {field_name}."
                raise ValueError(msg)

    properties = schema.get("properties", {})
    if isinstance(properties, Mapping):
        for field_name, field_schema in properties.items():
            if field_name in value and isinstance(field_schema, Mapping):
                _validate_json_type(
                    field_name=str(field_name),
                    expected=field_schema.get("type"),
                    value=value[field_name],
                )
                _validate_json_constraints(
                    field_name=str(field_name),
                    field_schema=field_schema,
                    value=value[field_name],
                )


def _validate_json_type(
    *,
    field_name: str,
    expected: object,
    value: object,
) -> None:
    """Validate one simple JSON-schema type declaration."""
    if expected is None:
        return
    expected_types = tuple(expected) if isinstance(expected, list) else (expected,)
    if "null" in expected_types and value is None:
        return

    validators: dict[str, type[object] | tuple[type[object], ...]] = {
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "object": dict,
        "array": list,
    }
    for expected_type in expected_types:
        validator = validators.get(str(expected_type))
        if validator is not None and isinstance(value, validator):
            return

    msg = f"Field '{field_name}' does not match expected type {expected!r}."
    raise ValueError(msg)


def _extract_json_payload(value: str) -> str:
    """Extract JSON object or array text, trimming fences and chatter."""
    stripped = _strip_json_fence(value).strip()
    first_obj = stripped.find("{")
    last_obj = stripped.rfind("}")
    if first_obj != -1 and last_obj != -1 and last_obj > first_obj:
        return stripped[first_obj : last_obj + 1]

    first_arr = stripped.find("[")
    last_arr = stripped.rfind("]")
    if first_arr != -1 and last_arr != -1 and last_arr > first_arr:
        return stripped[first_arr : last_arr + 1]

    return stripped


def _strip_json_fence(value: str) -> str:
    """Return JSON text without a simple Markdown code fence wrapper."""
    stripped = value.strip()
    if not stripped.startswith("```") or not stripped.endswith("```"):
        return value
    lines = stripped.splitlines()
    if len(lines) < _MIN_FENCED_JSON_LINES:
        return value
    if lines[0].strip() not in {"```", "```json", "```JSON"}:
        return value
    return "\n".join(lines[1:-1]).strip()


def _validate_json_constraints(
    *,
    field_name: str,
    field_schema: Mapping[str, Any],
    value: object,
) -> None:
    """Validate common shallow JSON-schema constraints."""
    min_length = field_schema.get("minLength")
    if (
        isinstance(min_length, int)
        and isinstance(value, str)
        and len(value) < min_length
    ):
        msg = f"Field '{field_name}' is shorter than minLength {min_length}."
        raise ValueError(msg)

    min_items = field_schema.get("minItems")
    if (
        isinstance(min_items, int)
        and isinstance(value, list)
        and len(value) < min_items
    ):
        msg = f"Field '{field_name}' has fewer items than minItems {min_items}."
        raise ValueError(msg)

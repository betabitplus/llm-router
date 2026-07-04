"""Gemini schema serialization helpers.

Why:
    Keeps Gemini-native response schemas and function parameters in the shape
    expected by Google-family HTTP and SDK APIs.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

_TYPE_LOOKUP = {
    "array": "ARRAY",
    "boolean": "BOOLEAN",
    "integer": "INTEGER",
    "number": "NUMBER",
    "object": "OBJECT",
    "string": "STRING",
}

_KEY_LOOKUP = {
    "anyOf": "any_of",
    "maxItems": "max_items",
    "maxLength": "max_length",
    "minItems": "min_items",
    "minLength": "min_length",
    "propertyOrdering": "property_ordering",
}

_DROPPED_KEYS = frozenset({"$defs", "$schema", "$id"})


def gemini_schema(
    schema: Mapping[str, Any],
    *,
    include_titles: bool = True,
    include_property_ordering: bool = True,
) -> dict[str, Any]:
    """Return a Gemini-native schema mapping from JSON Schema-like input."""
    schema = inline_schema_refs(schema)
    converted = _convert_schema(
        schema,
        include_titles=include_titles,
        include_property_ordering=include_property_ordering,
    )
    return converted if isinstance(converted, dict) else {}


def inline_schema_refs(schema: Mapping[str, Any]) -> dict[str, Any]:
    """Return a schema copy with local `$ref` values expanded."""
    defs = schema.get("$defs", {})
    inlined = _inline_schema_refs(schema, defs=defs)
    return inlined if isinstance(inlined, dict) else {}


def _inline_schema_refs(schema: object, *, defs: object) -> object:
    """Recursively replace local JSON Schema references with their targets."""
    if isinstance(schema, Mapping):
        ref = schema.get("$ref")
        if isinstance(ref, str) and isinstance(defs, Mapping):
            ref_name = ref.rsplit("/", maxsplit=1)[-1]
            target = defs.get(ref_name)
            if target is not None:
                return _inline_schema_refs(target, defs=defs)
        return {
            key: _inline_schema_refs(value, defs=defs)
            for key, value in schema.items()
            if key != "$defs"
        }
    if isinstance(schema, list):
        return [_inline_schema_refs(item, defs=defs) for item in schema]
    return schema


def _convert_schema(
    value: object,
    *,
    include_titles: bool,
    include_property_ordering: bool,
) -> object:
    """Recursively convert JSON Schema values into Gemini schema values."""
    if isinstance(value, Mapping):
        return _convert_schema_mapping(
            value,
            include_titles=include_titles,
            include_property_ordering=include_property_ordering,
        )
    if isinstance(value, list):
        return [
            _convert_schema(
                item,
                include_titles=include_titles,
                include_property_ordering=include_property_ordering,
            )
            for item in value
        ]
    return value


def _convert_schema_mapping(
    value: Mapping[object, object],
    *,
    include_titles: bool,
    include_property_ordering: bool,
) -> dict[str, Any]:
    """Convert one JSON Schema object into Gemini-compatible key names."""
    converted: dict[str, Any] = {}
    properties = value.get("properties")
    for raw_key, raw_item in value.items():
        key = str(raw_key)
        if _should_drop_schema_key(key, include_titles=include_titles):
            continue
        if key == "type":
            converted[key] = _convert_type(raw_item)
            continue
        converted[_KEY_LOOKUP.get(key, key)] = _convert_schema(
            raw_item,
            include_titles=include_titles,
            include_property_ordering=include_property_ordering,
        )
    _add_property_ordering(
        converted,
        properties=properties,
        include_property_ordering=include_property_ordering,
    )
    return converted


def _should_drop_schema_key(key: str, *, include_titles: bool) -> bool:
    """Return whether a schema key is unsupported for Gemini payloads."""
    return key in _DROPPED_KEYS or (key == "title" and not include_titles)


def _add_property_ordering(
    converted: dict[str, Any],
    *,
    properties: object,
    include_property_ordering: bool,
) -> None:
    """Add Gemini property ordering when requested and not already present."""
    if not include_property_ordering:
        return
    if "property_ordering" in converted:
        return
    if isinstance(properties, Mapping):
        converted["property_ordering"] = [str(name) for name in properties]


def _convert_type(value: object) -> object:
    """Convert JSON Schema primitive type names to Gemini enum names."""
    if isinstance(value, str):
        return _TYPE_LOOKUP.get(value, value)
    if isinstance(value, list):
        return [_convert_type(item) for item in value]
    return value

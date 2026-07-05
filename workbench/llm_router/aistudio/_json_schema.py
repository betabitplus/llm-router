# %%
"""AI Studio workbench JSON-schema helpers.

Why:
    AI Studio can mishandle `$ref` and `$defs` on the OpenAI-compatible path,
    so the workbench needs one explicit place to inline references before a
    live structured-output request.

When to use:
    Import from AI Studio workbench scripts that need a resolved
    `response_format` payload or need to inspect whether a schema still
    contains references.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


def resolve_refs(schema: Any, defs: dict[str, Any] | None = None) -> Any:  # noqa: ANN401
    """Recursively inline `$ref` values from a JSON schema."""
    if defs is None and isinstance(schema, dict):
        defs = schema.get("$defs", {})

    if isinstance(schema, dict):
        if "$ref" in schema:
            ref_name = str(schema["$ref"]).rsplit("/", maxsplit=1)[-1]
            if defs and ref_name in defs:
                return resolve_refs(defs[ref_name], defs)
            return schema

        return {
            key: resolve_refs(value, defs)
            for key, value in schema.items()
            if key != "$defs"
        }

    if isinstance(schema, list):
        return [resolve_refs(item, defs) for item in schema]

    return schema


def schema_has_key(schema: object, target_key: str) -> bool:
    """Return whether a nested schema object still contains `target_key`."""
    if isinstance(schema, dict):
        if target_key in schema:
            return True
        return any(schema_has_key(value, target_key) for value in schema.values())

    if isinstance(schema, list):
        return any(schema_has_key(item, target_key) for item in schema)

    return False


def build_json_schema_response_format(
    *,
    name: str,
    schema: dict[str, Any],
) -> dict[str, Any]:
    """Wrap a JSON schema in the OpenAI-compatible response_format shape."""
    return {
        "type": "json_schema",
        "json_schema": {
            "name": name,
            "schema": schema,
            "strict": True,
        },
    }


def build_resolved_response_format(schema_model: type[BaseModel]) -> dict[str, Any]:
    """Build a reference-free AI Studio response_format from a Pydantic model."""
    resolved_schema = resolve_refs(schema_model.model_json_schema())
    return build_json_schema_response_format(
        name=schema_model.__name__,
        schema=resolved_schema,
    )

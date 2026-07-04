"""OpenAI-compatible workbench structured-output helpers.

Why:
    Keeps reusable JSON-schema payloads in one place so each workbench script
    can stay about one provider seam instead of re-declaring large schemas.

When to use:
    Import from OpenAI-compatible workbench scripts that need one response
    format payload for structured JSON output.
"""

from __future__ import annotations

from typing import Any

# ======================================================================================
# Shared Schema Wrapper
# ======================================================================================


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


# ======================================================================================
# Text Schema
# ======================================================================================

LEGAL_CASE_RESPONSE_FORMAT = build_json_schema_response_format(
    name="LegalCaseSummary",
    schema={
        "type": "object",
        "properties": {
            "case_name": {"type": "string"},
            "court": {"type": "string"},
            "plaintiffs": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
            },
            "defendants": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
            },
            "legal_issues": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
            },
        },
        "required": [
            "case_name",
            "court",
            "plaintiffs",
            "defendants",
            "legal_issues",
        ],
    },
)


# ======================================================================================
# Image Schema
# ======================================================================================

SCENE_SUMMARY_RESPONSE_FORMAT = build_json_schema_response_format(
    name="SceneSummary",
    schema={
        "type": "object",
        "properties": {
            "primary_subject": {"type": "string"},
            "setting": {"type": "string"},
            "visible_objects": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 3,
            },
            "evidence": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 2,
            },
        },
        "required": [
            "primary_subject",
            "setting",
            "visible_objects",
            "evidence",
        ],
    },
)


# ======================================================================================
# Tool Schemas
# ======================================================================================

FORCED_TOOL_RESPONSE_FORMAT = build_json_schema_response_format(
    name="ForcedToolResult",
    schema={
        "type": "object",
        "properties": {
            "tool_name": {"type": "string"},
            "final_result": {"type": "integer"},
            "explanation": {"type": "string"},
        },
        "required": ["tool_name", "final_result", "explanation"],
    },
)


TOOL_LOOP_RESPONSE_FORMAT = build_json_schema_response_format(
    name="ToolLoopResult",
    schema={
        "type": "object",
        "properties": {
            "final_result": {"type": "integer"},
            "steps": {
                "type": "array",
                "minItems": 2,
                "items": {
                    "type": "object",
                    "properties": {
                        "tool_name": {"type": "string"},
                        "result": {"type": "integer"},
                    },
                    "required": ["tool_name", "result"],
                },
            },
        },
        "required": ["final_result", "steps"],
    },
)

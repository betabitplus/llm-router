from __future__ import annotations

import json

from llm_router._internal.providers.aistudio import inline_schema_refs


def test_inline_schema_refs_removes_defs_and_refs() -> None:
    schema = {
        "title": "Reply",
        "$defs": {
            "Answer": {
                "type": "object",
                "properties": {"text": {"type": "string"}},
            }
        },
        "properties": {"answer": {"$ref": "#/$defs/Answer"}},
    }

    resolved = inline_schema_refs(schema)

    encoded = json.dumps(resolved)
    assert "$defs" not in encoded
    assert "$ref" not in encoded
    assert resolved["properties"]["answer"]["properties"]["text"]["type"] == "string"

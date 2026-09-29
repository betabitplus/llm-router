# mutation-pin: REQ_STRUCTURED_SCHEMA_CONTRACT SM-AAB2D195
# pinned-by: claude-opus-5-5
from __future__ import annotations

from typing import Any

import pytest

from llm_router._internal.capabilities.schema import (
    SchemaSpec,
    with_schema_transform,
)

pytestmark = pytest.mark.verification_kind("unit")


def _identity(schema: Any) -> Any:
    return schema


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_transform_keeps_required_declared_via_composition() -> None:
    schema = {
        "type": "object",
        "allOf": [{"properties": {"count": {"type": "integer"}}}],
        "required": ["count"],
    }
    spec = SchemaSpec(name="counter", json_schema=schema, parser=int)

    result = with_schema_transform(spec, _identity)

    assert list(result.json_schema["required"]) == ["count"]
    assert result.json_schema["allOf"] == schema["allOf"]

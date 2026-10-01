# semantic-mutant: SM-BF818699
from __future__ import annotations

import pytest
from llm_router._internal.capabilities.schema import normalize_schema

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_normalize_schema_with_list_type_raises_type_error() -> None:
    schema = {
        "type": ["object"],
        "properties": {
            "title": {"type": "string"},
        },
        "required": ["title"],
    }
    with pytest.raises(TypeError, match=r"unhashable"):
        normalize_schema(schema)

# mutation-pin: REQ_STRUCTURED_SCHEMA_CONTRACT SM-4A74651D
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router._internal.capabilities.schema import _parse_mapping_schema

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_mapping_schema_keeps_extra_fields_allowed_by_schema() -> None:
    schema = {
        "type": "object",
        "properties": {"count": {"type": "integer", "minimum": 0}},
    }
    value = {"count": 5, "total": 12}

    result = _parse_mapping_schema(schema, value)

    assert result == {"count": 5, "total": 12}

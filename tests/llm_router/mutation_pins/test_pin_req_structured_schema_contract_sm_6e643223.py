# mutation-pin: REQ_STRUCTURED_SCHEMA_CONTRACT SM-6E643223
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router._internal.capabilities.schema import (
    _validate_mapping_schema_definition,
)

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_list_typed_non_object_schema_is_not_accepted() -> None:
    schema = {
        "type": ["array"],
        "items": {"type": "integer", "minimum": 0},
    }

    with pytest.raises(TypeError, match=r"unhashable"):
        _validate_mapping_schema_definition(schema)

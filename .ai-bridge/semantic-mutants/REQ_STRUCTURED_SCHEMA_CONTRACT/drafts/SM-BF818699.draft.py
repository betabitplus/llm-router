# semantic-mutant: SM-BF818699
from __future__ import annotations

import pytest

from llm_router._internal.capabilities.schema import (
    _validate_mapping_schema_definition,
)

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_list_valued_type_is_not_treated_as_plain_object_type() -> None:
    schema = {
        "type": ["object"],
        "properties": {"count": {"type": "integer", "minimum": 1}},
    }

    with pytest.raises(TypeError, match=r"unhashable"):
        _validate_mapping_schema_definition(schema)

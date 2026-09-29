# mutation-pin: REQ_STRUCTURED_SCHEMA_CONTRACT SM-07EEEA4D
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router._internal.capabilities.schema import (
    _validate_mapping_schema_definition,
)

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_invalid_schema_without_properties_is_rejected() -> None:
    schema = {"type": "object", "required": "count"}

    with pytest.raises(ValueError, match=r"valid Draft 2020-12 JSON Schema"):
        _validate_mapping_schema_definition(schema)

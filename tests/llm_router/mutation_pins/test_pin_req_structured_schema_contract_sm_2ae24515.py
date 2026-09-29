# mutation-pin: REQ_STRUCTURED_SCHEMA_CONTRACT SM-2AE24515
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router._internal.capabilities.schema import (
    SchemaSpec,
    validate_schema_output,
)

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_validation_returns_value_unchanged_with_none_fields() -> None:
    spec = SchemaSpec(name="test", json_schema={}, parser=dict)
    value = {"count": None, "label": "ok"}

    result = validate_schema_output(spec, value)

    assert result.valid is True
    assert result.value == {"count": None, "label": "ok"}

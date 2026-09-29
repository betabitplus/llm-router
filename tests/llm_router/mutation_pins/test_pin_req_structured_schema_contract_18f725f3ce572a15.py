# mutation-pin: REQ_STRUCTURED_SCHEMA_CONTRACT 18f725f3ce572a15
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router._internal.capabilities.schema import (
    SchemaSpec,
    normalize_schema,
)

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_mapping_schema_without_type_passes_normalization() -> None:
    schema = {"properties": {"answer": {"type": "string"}}}

    spec = normalize_schema(schema)

    assert isinstance(spec, SchemaSpec)
    assert spec.json_schema == schema

# mutation-pin: REQ_STRUCTURED_SCHEMA_CONTRACT 589c1fbde8e85997
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router._internal.capabilities.schema import normalize_schema

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_non_mapping_schema_is_rejected_during_normalization() -> None:
    invalid_schema: list[object] = []

    with pytest.raises(
        TypeError,
        match=r"response_schema must be a Pydantic model type or JSON schema mapping",
    ):
        normalize_schema(invalid_schema)

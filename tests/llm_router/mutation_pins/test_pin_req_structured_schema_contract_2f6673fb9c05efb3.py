# mutation-pin: REQ_STRUCTURED_SCHEMA_CONTRACT 2f6673fb9c05efb3
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router._internal.capabilities.schema import normalize_schema

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_non_object_mapping_schema_is_rejected_during_normalization() -> None:
    non_object_schema = {
        "title": "TextResponse",
        "type": "string",
    }

    with pytest.raises(
        ValueError,
        match=r"response_schema mapping must describe a JSON object\.",
    ):
        normalize_schema(non_object_schema)

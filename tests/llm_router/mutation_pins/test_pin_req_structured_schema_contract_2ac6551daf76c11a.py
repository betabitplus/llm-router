# mutation-pin: REQ_STRUCTURED_SCHEMA_CONTRACT 2ac6551daf76c11a
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router._internal.capabilities.schema import normalize_schema

pytestmark = pytest.mark.verification_kind("unit")


class PlainSchema:
    pass


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_normalize_schema_rejects_non_model_and_non_mapping_input() -> None:
    with pytest.raises(
        TypeError,
        match=r"^response_schema must be a Pydantic model type"
        r" or JSON schema mapping\.$",
    ):
        normalize_schema(PlainSchema)

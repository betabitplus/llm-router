# mutation-pin: REQ_STRUCTURED_SCHEMA_CONTRACT SM-C6EBF982
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest
from pydantic import BaseModel

from llm_router._internal.capabilities.schema import _parse_pydantic_model

pytestmark = pytest.mark.verification_kind("unit")


class RequiredNullable(BaseModel):
    x: int | None


class DefaultedNullable(BaseModel):
    y: int | None = 5


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_parse_pydantic_model_mapping_preserves_null_fields() -> None:
    required = _parse_pydantic_model(RequiredNullable, {"x": None})
    defaulted = _parse_pydantic_model(DefaultedNullable, {"y": None})

    assert isinstance(required, RequiredNullable)
    assert required.x is None
    assert isinstance(defaulted, DefaultedNullable)
    assert defaulted.y is None

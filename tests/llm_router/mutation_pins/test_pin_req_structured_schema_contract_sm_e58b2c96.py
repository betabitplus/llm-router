# mutation-pin: REQ_STRUCTURED_SCHEMA_CONTRACT SM-E58B2C96
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest
from pydantic import BaseModel, ConfigDict

from llm_router._internal.capabilities.schema import _parse_pydantic_model

pytestmark = pytest.mark.verification_kind("unit")


class Requested(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    answer: int


class Other(BaseModel):
    answer: int


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_parse_pydantic_model_does_not_return_other_model_instance() -> None:
    other = Other(answer=7)
    result = _parse_pydantic_model(Requested, other)

    assert result is not other
    assert isinstance(result, Requested)
    assert result.answer == 7

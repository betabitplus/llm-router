# mutation-pin: REQ_STRUCTURED_SCHEMA_CONTRACT 6e9116a1b83a69f4
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest
from pydantic import BaseModel

from llm_router._internal.capabilities.schema import _parse_pydantic_model

pytestmark = pytest.mark.verification_kind("unit")


class Answer(BaseModel):
    answer: int


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_parse_pydantic_model_returns_existing_instance() -> None:
    instance = Answer(answer=3)
    result = _parse_pydantic_model(Answer, instance)

    assert result is instance
    assert result is not None

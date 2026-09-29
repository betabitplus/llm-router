# mutation-pin: REQ_STRUCTURED_SCHEMA_CONTRACT a5d83d760dbc5183
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest
from pydantic import BaseModel

from llm_router._internal.capabilities.schema import _parse_pydantic_model

pytestmark = pytest.mark.verification_kind("unit")


class Answer(BaseModel):
    answer: int


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_parse_pydantic_model_from_dict() -> None:
    result = _parse_pydantic_model(Answer, {"answer": 3})

    assert isinstance(result, Answer)
    assert result == Answer(answer=3)
    assert result.answer == 3

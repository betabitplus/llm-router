# mutation-pin: REQ_STRUCTURED_SCHEMA_CONTRACT b6f8d3c681f933f8
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest
from pydantic import BaseModel

from llm_router._internal.capabilities.schema import _parse_pydantic_model

pytestmark = pytest.mark.verification_kind("unit")


class Answer(BaseModel):
    answer: int


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_parse_pydantic_model_with_dict_values() -> None:
    data = {"answer": 42}
    result = _parse_pydantic_model(Answer, data)

    assert isinstance(result, Answer)
    assert result == Answer(answer=42)

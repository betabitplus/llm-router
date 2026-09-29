# mutation-pin: REQ_STRUCTURED_SCHEMA_CONTRACT SM-D49276DB
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest
from pydantic import BaseModel

from llm_router._internal.capabilities.schema import _parse_pydantic_model

pytestmark = pytest.mark.verification_kind("unit")


class Answer(BaseModel):
    answer: int
    label: str


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_parse_pydantic_model_extracts_fenced_json_with_chatter() -> None:
    text = 'Here you go:\n```json\n{"answer": 42, "label": "ok"}\n```\nDone.'
    result = _parse_pydantic_model(Answer, text)

    assert isinstance(result, Answer)
    assert result.answer == 42
    assert result.label == "ok"

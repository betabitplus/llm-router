# mutation-pin: REQ_STRUCTURED_SCHEMA_CONTRACT SM-F375873A
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest
from pydantic import BaseModel, Field

from llm_router._internal.capabilities.schema import (
    normalize_schema,
    validate_schema_output,
)

pytestmark = pytest.mark.verification_kind("unit")


class Reply(BaseModel):
    final_answer: int = Field(alias="finalAnswer")


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_pydantic_schema_keeps_alias_and_rebuilds_from_alias_json() -> None:
    spec = normalize_schema(Reply)
    result = validate_schema_output(spec, '{"finalAnswer": 7}')

    assert spec.model_type is Reply
    assert dict(spec.json_schema) == Reply.model_json_schema()
    assert "finalAnswer" in spec.json_schema["properties"]
    assert "final_answer" not in spec.json_schema["properties"]
    assert result.valid is True
    assert isinstance(result.value, Reply)
    assert result.value == Reply(finalAnswer=7)

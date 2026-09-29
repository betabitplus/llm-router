# mutation-pin: REQ_STRUCTURED_SCHEMA_CONTRACT ffbbfd72fe94fb6f
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest
from pydantic import BaseModel, ValidationError

from llm_router._internal.capabilities.schema import (
    SchemaSpec,
    SchemaValidationResult,
    normalize_schema,
    validate_schema_output,
)

pytestmark = pytest.mark.verification_kind("unit")


class Answer(BaseModel):
    answer: int


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_pydantic_schema_parses_dict_output() -> None:
    spec = normalize_schema(Answer)
    assert isinstance(spec, SchemaSpec)

    valid_payload = {"answer": 3}
    result = validate_schema_output(spec, valid_payload)
    assert isinstance(result, SchemaValidationResult)
    assert result.valid is True
    assert isinstance(result.value, Answer)
    assert result.value == Answer(answer=3)
    assert result.value.answer == 3

    parsed = spec.parse(valid_payload)
    assert isinstance(parsed, Answer)
    assert parsed == Answer(answer=3)
    assert parsed.answer == 3

    with pytest.raises(ValidationError, match=r"answer"):
        spec.parse({"answer": "invalid"})

# mutation-pin: REQ_STRUCTURED_SCHEMA_CONTRACT SM-008E10B9
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest
from pydantic import BaseModel, computed_field

from llm_router._internal.capabilities.schema import (
    _pydantic_schema_spec,
    normalize_schema,
)

pytestmark = pytest.mark.verification_kind("unit")


class Invoice(BaseModel):
    amount: int
    currency: str = "USD"

    @computed_field
    def label(self) -> str:
        return f"{self.amount} {self.currency}"


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_pydantic_schema_uses_validation_mode_schema() -> None:
    expected = Invoice.model_json_schema()
    spec = _pydantic_schema_spec(Invoice)

    assert dict(spec.json_schema) == expected
    assert "label" not in spec.json_schema["properties"]
    assert "currency" not in spec.json_schema.get("required", [])
    assert dict(normalize_schema(Invoice).json_schema) == expected

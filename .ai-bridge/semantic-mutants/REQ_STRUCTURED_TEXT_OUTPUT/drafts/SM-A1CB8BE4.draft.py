# semantic-mutant: SM-A1CB8BE4
from __future__ import annotations

import pytest
from pydantic import BaseModel

from llm_router._internal.capabilities.schema import (
    SchemaSpec,
    validate_schema_output,
)

pytestmark = pytest.mark.verification_kind("unit")


class DockReport(BaseModel):
    """Report with an integer vehicle count."""

    vehicles: int


def _spec() -> SchemaSpec:
    return SchemaSpec(
        name="DockReport",
        json_schema=DockReport.model_json_schema(),
        parser=DockReport.model_validate,
    )


@pytest.mark.verifies("REQ_STRUCTURED_TEXT_OUTPUT[revision==2]")
def test_predecoded_dict_violating_schema_is_invalid() -> None:
    """A pre-decoded dict must still be checked against the schema."""
    result = validate_schema_output(_spec(), {"vehicles": "many"})

    assert result.valid is False
    assert result.value is None
    assert result.error_message


@pytest.mark.verifies("REQ_STRUCTURED_TEXT_OUTPUT[revision==2]")
def test_predecoded_dict_matching_schema_is_parsed() -> None:
    """A valid dict yields the parsed model, not the raw dict."""
    result = validate_schema_output(_spec(), {"vehicles": 5})

    assert result.valid is True
    assert isinstance(result.value, DockReport)
    assert result.value.vehicles == 5

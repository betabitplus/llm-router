# semantic-mutant: SM-B25D86B3
from __future__ import annotations

import pytest

from llm_router._internal.capabilities.tools import (
    ToolChoice,
    normalize_tool_choice,
)

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_TOOL_CHOICE[revision==2]")
def test_required_choice_without_registry_stays_required() -> None:
    choice = normalize_tool_choice("required", registry=None)

    assert choice == ToolChoice(kind="required")
    assert choice.kind == "required"
    assert choice.name is None
    assert choice.raw is None

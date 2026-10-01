# mutation-pin: TREQ_TOOL_REGISTRY 77986b22a0ac6322
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router._internal.capabilities.tools import ToolCall, ToolRegistry

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_TOOL_REGISTRY[revision==1]")
def test_execute_descriptor_only_tool_raises_value_error() -> None:
    tool_descriptor = {
        "name": "lookup",
        "description": "Lookup information.",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    }
    registry = ToolRegistry.from_tools([tool_descriptor])
    call = ToolCall(name="lookup", args={}, id="call_lookup")

    with pytest.raises(ValueError, match=r"Tool 'lookup' is a descriptor-only tool\."):
        registry.execute(call)

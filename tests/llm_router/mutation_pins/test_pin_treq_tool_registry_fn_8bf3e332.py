# mutation-pin: TREQ_TOOL_REGISTRY FN-8BF3E332
# pinned-by: delegate, one pin for 2 pins of ToolRegistry.execute
# kills: 77252785424d95f7 77986b22a0ac6322
from __future__ import annotations

import pytest

from llm_router._api.errors import ToolExecutionError
from llm_router._api.types import ToolCall
from llm_router._internal.capabilities.tools import ToolRegistry

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_TOOL_REGISTRY[revision==1]")
def test_execute_failure_and_descriptor_only_paths() -> None:
    original_cause = RuntimeError("boom")

    def failing_tool(value: int) -> int:
        if value > 0:
            raise original_cause
        return value

    descriptor = {
        "name": "lookup",
        "description": "Lookup information.",
        "parameters": {"type": "object", "properties": {}},
    }
    registry = ToolRegistry.from_tools([failing_tool, descriptor])

    failing_call = ToolCall(id="call_1", name="failing_tool", args={"value": 3})
    with pytest.raises(ToolExecutionError, match=r"failing_tool") as exc_info:
        registry.execute(failing_call)
    assert exc_info.value.tool_name == "failing_tool"
    assert exc_info.value.cause is original_cause
    assert exc_info.value.__cause__ is original_cause

    lookup_call = ToolCall(id="call_2", name="lookup", args={})
    with pytest.raises(
        ValueError, match=r"Tool 'lookup' is a descriptor-only tool\."
    ) as value_info:
        registry.execute(lookup_call)
    assert not isinstance(value_info.value, ToolExecutionError)

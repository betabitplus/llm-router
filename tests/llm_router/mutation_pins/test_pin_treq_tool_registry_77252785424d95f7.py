# mutation-pin: TREQ_TOOL_REGISTRY 77252785424d95f7
# pinned-by: claude-opus-5-5
"""Tests for ToolRegistry.execute error handling."""

from __future__ import annotations

import pytest

from llm_router._api.errors import ToolExecutionError
from llm_router._api.types import ToolCall
from llm_router._internal.capabilities.tools import ToolRegistry

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_TOOL_REGISTRY[revision==1]")
def test_execute_raises_tool_execution_error_on_callable_failure() -> None:
    original_cause = RuntimeError("Tool execution failed.")

    def failing_tool(value: int) -> int:
        if value > 0:
            raise original_cause
        return value

    registry = ToolRegistry.from_tools([failing_tool])
    call = ToolCall(
        id="call_1",
        name="failing_tool",
        args={"value": 42},
    )

    with pytest.raises(ToolExecutionError) as exc_info:
        registry.execute(call)

    assert exc_info.value.tool_name == "failing_tool"
    assert exc_info.value.cause is original_cause
    assert exc_info.value.__cause__ is original_cause

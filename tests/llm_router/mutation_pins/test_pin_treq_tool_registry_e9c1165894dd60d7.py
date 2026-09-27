# mutation-pin: TREQ_TOOL_REGISTRY e9c1165894dd60d7
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router._internal.capabilities.tools import (
    ToolCall,
    ToolRegistry,
    normalize_tool,
)

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_TOOL_REGISTRY[revision==1]")
def test_tool_registry_freezes_tools_mapping() -> None:
    def add(a: int, b: int) -> int:
        """Add two integers."""
        return a + b

    def multiply(a: int, b: int) -> int:
        """Multiply two integers."""
        return a * b

    add_tool = normalize_tool(add)
    multiply_tool = normalize_tool(multiply)

    source_tools = {add_tool.name: add_tool}
    registry = ToolRegistry(tools=source_tools)

    source_tools[add_tool.name] = multiply_tool
    source_tools["extra_tool"] = multiply_tool

    with pytest.raises(TypeError):
        registry.tools["assigned_tool"] = multiply_tool  # type: ignore[index]

    assert list(registry.tools.keys()) == [add_tool.name]
    assert registry.tools[add_tool.name] is add_tool
    assert registry.get(add_tool.name) is add_tool

    call = ToolCall(name=add_tool.name, args={"a": 3, "b": 4}, id="call_add_1")
    step = registry.execute(call)
    assert step.result == 7
    assert step.tool_name == add_tool.name
    assert step.args == {"a": 3, "b": 4}
    assert step.call_id == "call_add_1"

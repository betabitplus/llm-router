from __future__ import annotations

import pytest

from llm_router._internal.capabilities.tools import ToolRegistry, parse_tool_call


def add(a: int, b: int = 1) -> int:
    """Add two numbers."""
    return a + b


pytestmark = [
    pytest.mark.verifies("TREQ_TOOL_REGISTRY[revision==1]"),
    pytest.mark.verification_kind("unit"),
]


def test_callable_tool_schema_and_execution_match_python_signature() -> None:
    registry = ToolRegistry.from_tools([add])
    definition = registry.get("add")
    step = registry.execute(parse_tool_call({"name": "add", "args": {"a": 2}}))

    assert definition.parameters["required"] == ["a"]
    assert definition.parameters["properties"]["a"]["type"] == "integer"
    assert step.result == 3


def test_duplicate_tool_names_are_rejected() -> None:
    with pytest.raises(ValueError, match="Duplicate tool name"):
        ToolRegistry.from_tools([add, add])


@pytest.mark.parametrize(
    "payload",
    [
        {
            "id": "call-1",
            "function": {"name": "add", "arguments": '{"a": 2, "b": 5}'},
        },
        {"functionCall": {"name": "add", "args": {"a": 2, "b": 5}}},
    ],
)
def test_tool_call_parser_accepts_supported_provider_shapes(
    payload: dict[str, object],
) -> None:
    call = parse_tool_call(payload)

    assert call.name == "add"
    assert call.args == {"a": 2, "b": 5}

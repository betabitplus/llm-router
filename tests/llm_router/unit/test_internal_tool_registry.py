from __future__ import annotations

import pytest

from llm_router import ToolExecutionError
from llm_router._internal.capabilities.tools import (
    ToolLoopState,
    ToolRegistry,
    normalize_tool,
    normalize_tool_choice,
    parse_tool_call,
    run_tool_round,
)


def add(a: int, b: int = 1) -> int:
    """Add two numbers."""
    return a + b


def fail_tool(value: str) -> str:
    raise RuntimeError(f"bad {value}")


def test_callable_tool_normalizes_signature_and_executes() -> None:
    registry = ToolRegistry.from_tools([add])
    definition = registry.get("add")

    assert definition.description == "Add two numbers."
    assert definition.parameters["required"] == ["a"]
    assert definition.parameters["properties"]["a"]["type"] == "integer"

    step = registry.execute(parse_tool_call({"name": "add", "args": {"a": 2}}))

    assert step.tool_name == "add"
    assert step.args == {"a": 2}
    assert step.result == 3


def test_mapping_tool_preserves_descriptor_without_callable() -> None:
    descriptor = {
        "type": "function",
        "function": {
            "name": "lookup",
            "description": "Lookup data",
            "parameters": {"type": "object"},
        },
    }

    definition = normalize_tool(descriptor)

    assert definition.name == "lookup"
    assert definition.description == "Lookup data"
    assert definition.descriptor == descriptor


def test_duplicate_tool_names_fail() -> None:
    with pytest.raises(ValueError, match="Duplicate tool name"):
        ToolRegistry.from_tools([add, add])


def test_tool_choice_normalizes_named_and_provider_raw_shapes() -> None:
    registry = ToolRegistry.from_tools([add])

    named = normalize_tool_choice("add", registry=registry)
    raw = normalize_tool_choice(
        {"type": "function", "function": {"name": "add"}},
        registry=registry,
    )

    assert normalize_tool_choice(None).kind == "auto"
    assert normalize_tool_choice("none").kind == "none"
    assert named.kind == "named"
    assert named.name == "add"
    assert raw.kind == "raw"
    assert raw.name == "add"


def test_parse_tool_call_accepts_openai_style_arguments() -> None:
    call = parse_tool_call(
        {
            "id": "call-1",
            "function": {
                "name": "add",
                "arguments": '{"a": 2, "b": 5}',
            },
        }
    )

    assert call.id == "call-1"
    assert call.name == "add"
    assert call.args == {"a": 2, "b": 5}
    assert call.raw_arguments == '{"a": 2, "b": 5}'


def test_tool_execution_errors_use_public_exception() -> None:
    registry = ToolRegistry.from_tools([fail_tool])

    with pytest.raises(ToolExecutionError) as exc_info:
        registry.execute(parse_tool_call({"name": "fail_tool", "args": {"value": "x"}}))

    assert exc_info.value.tool_name == "fail_tool"
    assert "value=x" in str(exc_info.value)
    assert isinstance(exc_info.value.cause, RuntimeError)


def test_tool_round_stops_at_max_rounds_with_outstanding_calls() -> None:
    registry = ToolRegistry.from_tools([add])
    first = run_tool_round(
        state=ToolLoopState(max_rounds=1),
        tool_calls=[{"name": "add", "args": {"a": 1, "b": 2}}],
        registry=registry,
    )
    second = run_tool_round(
        state=first,
        tool_calls=[{"name": "add", "args": {"a": 5}}],
        registry=registry,
    )

    assert first.completed_rounds == 1
    assert first.steps[0].result == 3
    assert second.completed_rounds == 1
    assert second.steps == first.steps
    assert [call.name for call in second.outstanding_tool_calls] == ["add"]


def test_parse_tool_call_accepts_google_function_call_shape() -> None:
    call = parse_tool_call(
        {
            "functionCall": {
                "name": "add",
                "args": {"a": 3, "b": 4},
            }
        }
    )

    assert call.name == "add"
    assert call.args == {"a": 3, "b": 4}

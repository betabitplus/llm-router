from __future__ import annotations

import pytest

from llm_router._internal.capabilities.tools import ToolRegistry, parse_tool_call
from tests.llm_router.support.fault_observation import retain_local_fault_injection


def add(a: int, b: int = 1) -> int:
    """Add two numbers."""
    return a + b


pytestmark = [
    pytest.mark.verifies("TREQ_TOOL_REGISTRY[revision==1]"),
    pytest.mark.verification_kind("unit"),
]


@pytest.mark.coverage_item("VC_TOOL_REGISTRY_SCHEMA_EXECUTION")
def test_callable_tool_schema_and_execution_match_python_signature() -> None:
    registry = ToolRegistry.from_tools([add])
    definition = registry.get("add")
    step = registry.execute(parse_tool_call({"name": "add", "args": {"a": 2}}))

    assert definition.parameters["required"] == ["a"]
    assert definition.parameters["properties"]["a"]["type"] == "integer"
    assert step.result == 3


@pytest.mark.coverage_item("VC_TOOL_REGISTRY_DUPLICATE_REJECTION")
def test_duplicate_tool_names_are_rejected() -> None:
    with pytest.raises(ValueError, match="Duplicate tool name"):
        ToolRegistry.from_tools([add, add])


@pytest.mark.coverage_item("VC_TOOL_REGISTRY_CALL_SHAPES")
@pytest.mark.parametrize(
    "payload",
    [
        {
            "id": "call-1",
            "function": {"name": "add", "arguments": '{"a": 2, "b": 5}'},
        },
        {"functionCall": {"name": "add", "args": {"a": 2, "b": 5}}},
    ],
    ids=["openai-function", "google-function"],
)
@pytest.mark.coverage_path("case-id")
def test_tool_call_parser_accepts_supported_provider_shapes(
    payload: dict[str, object],
) -> None:
    call = parse_tool_call(payload)

    assert call.name == "add"
    assert call.args == {"a": 2, "b": 5}


@pytest.mark.fault_item("TREQ_TOOL_REGISTRY", "interface.payload-schema")
@pytest.mark.parametrize(
    ("payload", "error", "message"),
    [
        ({"function": {"arguments": '{"a": 2}'}}, ValueError, "missing a name"),
        (
            {"functionCall": {"name": "add", "args": [2, 5]}},
            TypeError,
            "must be a mapping",
        ),
    ],
    ids=["openai-without-name", "google-args-not-a-mapping"],
)
def test_tool_call_parser_refuses_a_shape_its_schema_does_not_allow(
    payload: dict[str, object],
    error: type[Exception],
    message: str,
) -> None:
    retain_local_fault_injection(
        contract_id="TREQ_TOOL_REGISTRY",
        fault_class="interface.payload-schema",
        mechanism=(
            "a provider tool call without its name, or with arguments that are "
            "not a mapping"
        ),
    )
    with pytest.raises(error, match=message):
        parse_tool_call(payload)

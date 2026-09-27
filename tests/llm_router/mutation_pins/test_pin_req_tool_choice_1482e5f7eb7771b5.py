# mutation-pin: REQ_TOOL_CHOICE 1482e5f7eb7771b5
# pinned-by: claude-opus-5-5: The requirement says both public named-choice forms must normalize to the same selected registered tool. With the mutant, the mapping form accepts a tool name that isn't in the registry, while the string form rejects it. The two forms no longer agree, and a named choice can point at a tool that can'
from __future__ import annotations

import dataclasses
from typing import Any

import pytest
import llm_router._internal.capabilities.tools as tools_module
from llm_router._internal.capabilities.tools import ToolRegistry, normalize_tool_choice

pytestmark = pytest.mark.verification_kind("unit")


def _create_registry_with_tool(tool_name: str) -> ToolRegistry:
    registry = ToolRegistry()

    def sample_tool() -> str:
        """Sample tool for registry verification."""
        return "ok"

    sample_tool.__name__ = tool_name
    setattr(sample_tool, "name", tool_name)

    def _is_registered(reg: ToolRegistry) -> bool:
        try:
            res = normalize_tool_choice(tool_name, registry=reg)
            return res.name == tool_name
        except Exception:
            return False

    if _is_registered(registry):
        return registry

    tool_obj: Any = sample_tool
    tool_cls = getattr(tools_module, "Tool", None) or getattr(tools_module, "ToolDefinition", None)
    if tool_cls is not None:
        try:
            tool_obj = tool_cls(name=tool_name)
        except Exception:
            try:
                tool_obj = tool_cls(name=tool_name, func=sample_tool)
            except Exception:
                try:
                    tool_obj = tool_cls(name=tool_name, description="test")
                except Exception:
                    tool_obj = sample_tool

    for method_name in ("add", "add_tool", "register_tool", "append"):
        if hasattr(registry, method_name):
            method = getattr(registry, method_name)
            for candidate in (tool_obj, sample_tool):
                try:
                    method(candidate)
                    if _is_registered(registry):
                        return registry
                except Exception:
                    pass

    try:
        registry[tool_name] = tool_obj
        if _is_registered(registry):
            return registry
    except Exception:
        pass

    for attr in ("tools", "_tools", "by_name", "_by_name", "registry", "_registry"):
        if hasattr(registry, attr):
            container = getattr(registry, attr)
            if isinstance(container, dict):
                container[tool_name] = tool_obj
                if _is_registered(registry):
                    return registry
            elif isinstance(container, list):
                container.append(tool_obj)
                if _is_registered(registry):
                    return registry
            elif isinstance(container, set):
                container.add(tool_name)
                if _is_registered(registry):
                    return registry

    if dataclasses.is_dataclass(registry):
        for f in dataclasses.fields(registry):
            container = getattr(registry, f.name)
            if isinstance(container, dict):
                container[tool_name] = tool_obj
                if _is_registered(registry):
                    return registry
            elif isinstance(container, list):
                container.append(tool_obj)
                if _is_registered(registry):
                    return registry

    for factory in (ToolRegistry, getattr(ToolRegistry, "from_tools", None), getattr(ToolRegistry, "from_functions", None)):
        if factory is None:
            continue
        for candidate in ([sample_tool], [tool_obj], {tool_name: sample_tool}, {tool_name: tool_obj}):
            try:
                reg = factory(candidate)
                if _is_registered(reg):
                    return reg
            except Exception:
                pass
            try:
                reg = factory(tools=candidate)
                if _is_registered(reg):
                    return reg
            except Exception:
                pass

    return registry


@pytest.mark.verifies("REQ_TOOL_CHOICE[revision==1]")
def test_named_tool_choice_mapping_validates_existence_and_matches_string_choice() -> None:
    missing_tool_name = "fetch_weather_forecast"
    missing_mapping_choice = {
        "name": missing_tool_name,
        "type": "function",
        "function": {"name": missing_tool_name},
    }
    empty_registry = ToolRegistry()

    with pytest.raises(KeyError) as string_exc:
        normalize_tool_choice(missing_tool_name, registry=empty_registry)

    with pytest.raises(KeyError) as mapping_exc:
        normalize_tool_choice(missing_mapping_choice, registry=empty_registry)

    assert mapping_exc.type is string_exc.type
    assert mapping_exc.value.args == string_exc.value.args

    registered_tool_name = "calculate_order_discount"
    registered_mapping_choice = {
        "name": registered_tool_name,
        "type": "function",
        "function": {"name": registered_tool_name},
    }
    registered_registry = _create_registry_with_tool(registered_tool_name)

    string_choice = normalize_tool_choice(registered_tool_name, registry=registered_registry)
    mapping_choice = normalize_tool_choice(registered_mapping_choice, registry=registered_registry)

    assert string_choice.name == registered_tool_name
    assert mapping_choice.name == string_choice.name

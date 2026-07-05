"""Tool normalization and execution helpers.

Why:
    Keeps local Python tool execution and public tool traces independent of
    provider-specific tool-call payloads.
"""

from __future__ import annotations

import inspect
import json
from collections.abc import Callable, Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Literal, get_type_hints

from llm_router._internal.contracts.models import ToolCall, ToolStep
from llm_router._internal.contracts.errors import ToolExecutionError


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    """Provider-neutral tool definition."""

    name: str
    description: str | None
    parameters: Mapping[str, Any]
    descriptor: Mapping[str, Any]
    callable: Callable[..., Any] | None = None

    def __post_init__(self) -> None:
        """Copy mutable mappings after construction."""
        object.__setattr__(
            self,
            "parameters",
            MappingProxyType(deepcopy(dict(self.parameters))),
        )
        object.__setattr__(
            self,
            "descriptor",
            MappingProxyType(deepcopy(dict(self.descriptor))),
        )


@dataclass(frozen=True, slots=True)
class ToolChoice:
    """Normalized tool-choice policy."""

    kind: Literal["auto", "none", "required", "named", "raw"]
    name: str | None = None
    raw: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        """Copy raw provider choice mappings after construction."""
        if self.raw is not None:
            object.__setattr__(self, "raw", MappingProxyType(deepcopy(dict(self.raw))))


@dataclass(frozen=True, slots=True)
class ToolLoopState:
    """Provider-neutral tool loop state for one request."""

    max_rounds: int
    completed_rounds: int = 0
    steps: tuple[ToolStep, ...] = ()
    outstanding_tool_calls: tuple[ToolCall, ...] = ()

    def can_execute_tools(self) -> bool:
        """Return whether another local tool round can run."""
        return self.completed_rounds < self.max_rounds


@dataclass(frozen=True, slots=True)
class ToolRegistry:
    """Lookup and execution registry for normalized tools."""

    tools: Mapping[str, ToolDefinition] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Freeze tool mapping after construction."""
        object.__setattr__(self, "tools", MappingProxyType(dict(self.tools)))

    @classmethod
    def from_tools(
        cls,
        tools: Sequence[Callable[..., Any] | Mapping[str, Any]],
    ) -> ToolRegistry:
        """Normalize public tool inputs into a registry."""
        definitions = [normalize_tool(tool) for tool in tools]
        mapping: dict[str, ToolDefinition] = {}
        for definition in definitions:
            if definition.name in mapping:
                msg = f"Duplicate tool name: {definition.name}."
                raise ValueError(msg)
            mapping[definition.name] = definition
        return cls(tools=mapping)

    def get(self, name: str) -> ToolDefinition:
        """Return a normalized tool definition by name."""
        try:
            return self.tools[name]
        except KeyError as exc:
            msg = f"Unknown tool: {name}."
            raise KeyError(msg) from exc

    def execute(self, call: ToolCall) -> ToolStep:
        """Execute one normalized tool call and return its public trace step."""
        definition = self.get(call.name)
        if definition.callable is None:
            msg = f"Tool '{call.name}' is a descriptor-only tool."
            raise ValueError(msg)
        try:
            result = definition.callable(**call.args)
        except Exception as exc:
            raise ToolExecutionError(
                tool_name=call.name,
                args=dict(call.args),
                cause=exc,
            ) from exc
        return ToolStep(
            tool_name=call.name,
            args=dict(call.args),
            result=result,
            call_id=call.id,
        )


def normalize_tool(tool: object) -> ToolDefinition:
    """Normalize one public callable or dict tool declaration."""
    if callable(tool):
        return _callable_tool(tool)
    if isinstance(tool, Mapping):
        return _mapping_tool(tool)

    msg = "tools must be callables or mapping descriptors."
    raise TypeError(msg)


def normalize_tool_choice(
    choice: object,
    *,
    registry: ToolRegistry | None = None,
) -> ToolChoice:
    """Normalize public tool-choice input."""
    if choice is None or choice == "auto":
        return ToolChoice(kind="auto")
    if choice == "none":
        return ToolChoice(kind="none")
    if choice == "required":
        return ToolChoice(kind="required")
    if isinstance(choice, str):
        _require_tool_exists(choice, registry=registry)
        return ToolChoice(kind="named", name=choice)
    if isinstance(choice, Mapping):
        copied = deepcopy(dict(choice))
        name = _tool_choice_name(copied)
        if name is not None:
            _require_tool_exists(name, registry=registry)
        return ToolChoice(kind="raw", name=name, raw=copied)

    msg = "tool_choice must be a string, mapping, or None."
    raise TypeError(msg)


def parse_tool_call(raw: object) -> ToolCall:
    """Parse provider-neutral or provider-shaped tool call data."""
    if isinstance(raw, ToolCall):
        return raw
    if not isinstance(raw, Mapping):
        msg = "tool call must be a ToolCall or mapping."
        raise TypeError(msg)

    name, raw_arguments, args = _tool_call_components(raw)
    if not isinstance(name, str) or not name:
        msg = "tool call is missing a name."
        raise ValueError(msg)
    if not isinstance(args, dict):
        msg = "tool call args must be a mapping."
        raise TypeError(msg)

    call_id = raw.get("id")
    return ToolCall(
        id=call_id if isinstance(call_id, str) else None,
        name=name,
        args={str(key): value for key, value in args.items()},
        raw_arguments=raw_arguments if isinstance(raw_arguments, str) else None,
    )


def _tool_call_components(
    data: Mapping[object, object],
) -> tuple[object, object, object]:
    """Extract name, raw arguments, and parsed args from provider tool data."""
    function_call = data.get("functionCall")
    if isinstance(function_call, Mapping):
        return (
            function_call.get("name"),
            function_call.get("args"),
            _parse_call_args(function_call.get("args")),
        )

    function = data.get("function")
    if isinstance(function, Mapping):
        return (
            function.get("name"),
            function.get("arguments"),
            _parse_call_args(function.get("arguments")),
        )

    raw_arguments = data.get("raw_arguments") or data.get("arguments")
    return (
        data.get("name"),
        raw_arguments,
        data.get("args", _parse_call_args(raw_arguments)),
    )


def run_tool_round(
    *,
    state: ToolLoopState,
    tool_calls: Sequence[ToolCall | Mapping[str, Any]],
    registry: ToolRegistry,
) -> ToolLoopState:
    """Advance tool-loop state by executing one round when allowed."""
    parsed_calls = tuple(parse_tool_call(call) for call in tool_calls)
    if not state.can_execute_tools():
        return ToolLoopState(
            max_rounds=state.max_rounds,
            completed_rounds=state.completed_rounds,
            steps=state.steps,
            outstanding_tool_calls=parsed_calls,
        )

    steps = tuple(registry.execute(call) for call in parsed_calls)
    return ToolLoopState(
        max_rounds=state.max_rounds,
        completed_rounds=state.completed_rounds + 1,
        steps=(*state.steps, *steps),
        outstanding_tool_calls=(),
    )


def _callable_tool(function: Callable[..., Any]) -> ToolDefinition:
    """Build a normalized tool definition from a Python callable."""
    name = function.__name__
    parameters = _parameters_from_signature(
        inspect.signature(function),
        name=name,
        type_hints=get_type_hints(function),
    )
    description = inspect.getdoc(function)
    descriptor = {
        "type": "function",
        "function": {
            "name": name,
            "description": description or "",
            "parameters": parameters,
        },
    }
    return ToolDefinition(
        name=name,
        description=description,
        parameters=parameters,
        descriptor=descriptor,
        callable=function,
    )


def _mapping_tool(tool: Mapping[str, Any]) -> ToolDefinition:
    """Build a normalized tool definition from a mapping descriptor."""
    copied = deepcopy(dict(tool))
    function = copied.get("function")
    source = function if isinstance(function, Mapping) else copied
    name = source.get("name")
    if not isinstance(name, str) or not name:
        msg = "tool descriptor is missing a function name."
        raise ValueError(msg)
    description = source.get("description")
    parameters = source.get("parameters", {})
    if not isinstance(parameters, Mapping):
        msg = "tool descriptor parameters must be a mapping."
        raise TypeError(msg)
    return ToolDefinition(
        name=name,
        description=description if isinstance(description, str) else None,
        parameters=parameters,
        descriptor=copied,
    )


def _parameters_from_signature(
    signature: inspect.Signature,
    *,
    name: str,
    type_hints: Mapping[str, object],
) -> dict[str, Any]:
    """Return a compact JSON-schema object for callable parameters."""
    properties: dict[str, Any] = {}
    required: list[str] = []
    for param_name, parameter in signature.parameters.items():
        if parameter.kind in {
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        }:
            continue
        annotation = type_hints.get(param_name, parameter.annotation)
        properties[param_name] = {
            "title": _schema_title(param_name),
            "type": _json_type_for_annotation(annotation),
        }
        if parameter.default is inspect.Parameter.empty:
            required.append(param_name)
    return {
        "type": "object",
        "title": f"{name}Args",
        "properties": properties,
        "required": required,
    }


def _schema_title(name: str) -> str:
    """Return a compact JSON-schema title for a Python parameter name."""
    return name[:1].upper() + name[1:]


def _json_type_for_annotation(annotation: object) -> str:
    """Return a simple JSON type name for a Python annotation."""
    annotation_map: dict[object, str] = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
    }
    return annotation_map.get(annotation, "object")


def _tool_choice_name(choice: Mapping[str, Any]) -> str | None:
    """Extract a named tool from common provider choice mappings."""
    function = choice.get("function")
    if isinstance(function, Mapping) and isinstance(function.get("name"), str):
        return function["name"]
    if isinstance(choice.get("name"), str):
        return choice["name"]
    return None


def _require_tool_exists(name: str, *, registry: ToolRegistry | None) -> None:
    """Validate a named tool choice when a registry is available."""
    if registry is None:
        return
    registry.get(name)


def _parse_call_args(raw_arguments: object) -> dict[str, Any]:
    """Parse tool-call arguments from mapping or JSON text."""
    if raw_arguments is None:
        return {}
    if isinstance(raw_arguments, Mapping):
        return {str(key): value for key, value in raw_arguments.items()}
    if isinstance(raw_arguments, str):
        try:
            parsed = json.loads(raw_arguments)
        except json.JSONDecodeError as exc:
            msg = f"Tool call arguments are not valid JSON: {exc.msg}."
            raise ValueError(msg) from exc
        if not isinstance(parsed, dict):
            msg = "Tool call arguments must decode to a JSON object."
            raise TypeError(msg)
        return parsed

    msg = "Tool call arguments must be a mapping, JSON string, or None."
    raise TypeError(msg)

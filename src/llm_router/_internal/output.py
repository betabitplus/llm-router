"""Public response assembly helpers.

Why:
    Converts internal provider and routing outcomes into stable public response
    DTOs at the runtime boundary.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, is_dataclass
from typing import cast

from pydantic import BaseModel

from llm_router._api.contracts import LLMRouterResponse, ToolCall, ToolStep
from llm_router._internal.providers.base import ProviderResult
from llm_router._support.error_formatting import preview_value


class _PublicDataMapping(dict[str, object]):
    """JSON-safe mapping that also supports attribute-style access."""

    def __getattr__(self, name: str) -> object:
        """Return mapping values through attribute access for legacy callers."""
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


def build_public_response(
    result: ProviderResult,
    *,
    output_text: str | None = None,
    tool_calls: Sequence[ToolCall] | None = None,
    tool_trace: Sequence[ToolStep] = (),
    structured_data: object | None = None,
) -> LLMRouterResponse:
    """Build the public success DTO from one normalized provider result."""
    data = _json_safe_value(result.data)
    if structured_data is not None and isinstance(data, dict) and "parsed" not in data:
        data = {**data, "parsed": _json_safe_value(structured_data)}
    return LLMRouterResponse(
        data=data,
        usage=result.usage,
        provider=result.provider.value,
        model=result.model.value,
        output_text=result.output_text if output_text is None else output_text,
        tool_calls=list(result.tool_calls if tool_calls is None else tool_calls),
        tool_trace=list(tool_trace),
    )


def _json_safe_value(value: object) -> object:
    """Return a JSON-safe value without leaking SDK objects through `data`."""
    if _is_json_scalar(value):
        return value
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if _is_dataclass_instance(value):
        return _json_safe_value(asdict(value))
    if isinstance(value, Mapping):
        return _PublicDataMapping(
            {str(key): _json_safe_value(item) for key, item in value.items()}
        )
    if _is_json_sequence(value):
        return [_json_safe_value(item) for item in cast("Sequence[object]", value)]
    return {"type": type(value).__name__, "preview": preview_value(value)}


def _is_json_scalar(value: object) -> bool:
    """Return whether `value` can pass through public data unchanged."""
    return value is None or isinstance(value, str | int | float | bool)


def _is_dataclass_instance(value: object) -> bool:
    """Return whether `value` is a dataclass instance rather than a class."""
    return is_dataclass(value) and not isinstance(value, type)


def _is_json_sequence(value: object) -> bool:
    """Return whether `value` should be recursively converted as a sequence."""
    excluded_types = str | bytes | bytearray
    return isinstance(value, Sequence) and not isinstance(value, excluded_types)

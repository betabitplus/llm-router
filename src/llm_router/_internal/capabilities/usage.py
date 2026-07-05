"""Provider usage normalization.

Why:
    Converts provider usage payloads into the stable public `UsageStats` shape.
"""

from __future__ import annotations

from collections.abc import Mapping

from llm_router._api.types import UsageStats

_INPUT_KEYS = (
    "input_tokens",
    "prompt_tokens",
    "prompt_token_count",
    "promptTokenCount",
)
_OUTPUT_KEYS = (
    "output_tokens",
    "completion_tokens",
    "candidates_token_count",
    "candidatesTokenCount",
)
_TOTAL_KEYS = ("total_tokens", "total_token_count", "totalTokenCount")
_NESTED_USAGE_KEYS = ("usage", "usage_metadata", "usageMetadata")


def normalize_usage(value: object) -> UsageStats | None:
    """Normalize common provider usage payloads into public usage stats."""
    if value is None:
        return None
    if isinstance(value, UsageStats):
        return value

    input_tokens = _first_int(value, _INPUT_KEYS)
    output_tokens = _first_int(value, _OUTPUT_KEYS)
    total_tokens = _first_int(value, _TOTAL_KEYS)
    if total_tokens == 0 and (input_tokens or output_tokens):
        total_tokens = input_tokens + output_tokens

    return UsageStats(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
    )


def _first_int(value: object, keys: tuple[str, ...]) -> int:
    """Return the first non-negative integer-like value from a payload."""
    for key in keys:
        raw = _get_value(value, key)
        if raw is None:
            continue
        try:
            parsed = int(raw)
        except (TypeError, ValueError):
            continue
        return max(0, parsed)
    return 0


def _get_value(value: object, key: str) -> object | None:
    """Read a usage field from mappings, objects, or nested `usage` payloads."""
    if isinstance(value, Mapping):
        if key in value:
            return value[key]
        for nested_key in _NESTED_USAGE_KEYS:
            nested = value.get(nested_key)
            if isinstance(nested, Mapping) and key in nested:
                return nested[key]
        return None

    if hasattr(value, key):
        return getattr(value, key)
    for nested_key in _NESTED_USAGE_KEYS:
        nested = getattr(value, nested_key, None)
        if nested is not None and hasattr(nested, key):
            return getattr(nested, key)
    return None

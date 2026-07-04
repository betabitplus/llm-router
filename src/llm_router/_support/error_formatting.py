"""Safe preview helpers for exception and value formatting.

Why:
    Keeps bounded exception and value previews consistent across public errors
    and structured logs.

When to use:
    Import from here when code needs a short caller-safe preview of arbitrary
    values, mappings, or exception messages.

Notes:
    These helpers centralize preview formatting, but they do not replace
    source-level redaction discipline.
"""

from __future__ import annotations

from collections.abc import Mapping
from reprlib import Repr
from textwrap import shorten
from typing import Any

_MAX_PREVIEW_CHARS = 160
_MAX_MAPPING_ITEMS = 4
_EMPTY_PREVIEW = "<empty>"
_ELLIPSIS = "..."


def _repr_formatter(*, max_chars: int) -> Repr:
    """Return a stdlib reprlib formatter tuned for bounded previews."""
    formatter = Repr()
    formatter.maxstring = max_chars
    formatter.maxother = max_chars
    formatter.maxlong = max_chars
    formatter.maxlist = _MAX_MAPPING_ITEMS
    formatter.maxtuple = _MAX_MAPPING_ITEMS
    formatter.maxset = _MAX_MAPPING_ITEMS
    formatter.maxfrozenset = _MAX_MAPPING_ITEMS
    formatter.maxdict = _MAX_MAPPING_ITEMS
    return formatter


def preview_text(value: str, *, max_chars: int = _MAX_PREVIEW_CHARS) -> str:
    """Return a single-line bounded preview for text values."""
    collapsed = " ".join(value.split())
    if not collapsed:
        return _EMPTY_PREVIEW
    return shorten(collapsed, width=max_chars, placeholder=_ELLIPSIS)


def preview_value(value: object, *, max_chars: int = _MAX_PREVIEW_CHARS) -> str:
    """Return a bounded preview for an arbitrary value."""
    if isinstance(value, str):
        return preview_text(value, max_chars=max_chars)
    if isinstance(value, bytes):
        decoded = value.decode("utf-8", errors="replace")
        return preview_text(decoded, max_chars=max_chars)

    try:
        rendered = _repr_formatter(max_chars=max_chars).repr(value)
    except Exception:  # defensive: arbitrary objects can fail during repr
        rendered = f"<{type(value).__name__}>"
    return preview_text(rendered, max_chars=max_chars)


def preview_mapping(
    mapping: Mapping[str, Any],
    *,
    max_items: int = _MAX_MAPPING_ITEMS,
    value_max_chars: int = 40,
) -> str:
    """Return a bounded preview for a small mapping."""
    if not mapping:
        return "{}"

    parts: list[str] = []
    items = list(mapping.items())
    for key, value in items[:max_items]:
        parts.append(f"{key}={preview_value(value, max_chars=value_max_chars)}")

    suffix = ", ..." if len(items) > max_items else ""
    return "{" + ", ".join(parts) + suffix + "}"


def preview_exception_message(
    exc: BaseException,
    *,
    max_chars: int = _MAX_PREVIEW_CHARS,
) -> str:
    """Return a bounded message preview for an exception."""
    message = str(exc).strip()
    if not message:
        return type(exc).__name__
    return preview_text(message, max_chars=max_chars)

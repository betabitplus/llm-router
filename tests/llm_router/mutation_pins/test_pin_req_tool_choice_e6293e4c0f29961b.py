# mutation-pin: REQ_TOOL_CHOICE e6293e4c0f29961b
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
"""Pin: a read-only Mapping tool choice is accepted and copied."""

from __future__ import annotations

import typing
from typing import Any

import pytest

from llm_router._internal.capabilities.tools import (
    ToolRegistry,
    normalize_tool_choice,
)

pytestmark = pytest.mark.verification_kind("unit")


class ReadOnlyChoice(typing.Mapping[str, Any]):
    """A read-only Mapping, like a mapping proxy, that cannot be deep-copied."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = dict(data)

    def __getitem__(self, name: str) -> Any:
        return self._data[name]

    def __iter__(self) -> typing.Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __deepcopy__(self, memo: dict[int, Any]) -> ReadOnlyChoice:
        msg = "cannot deep-copy a read-only mapping"
        raise TypeError(msg)


def add(*, a: int, b: int) -> int:
    return a + b


@pytest.mark.verifies("REQ_TOOL_CHOICE[revision==2]")
def test_named_read_only_mapping_choice_normalizes_to_raw() -> None:
    registry = ToolRegistry.from_tools([add])
    payload = {"type": "function", "function": {"name": "add"}}

    normalized = normalize_tool_choice(ReadOnlyChoice(payload), registry=registry)

    assert normalized.kind == "raw"
    assert normalized.name == "add"
    assert normalized.raw == payload

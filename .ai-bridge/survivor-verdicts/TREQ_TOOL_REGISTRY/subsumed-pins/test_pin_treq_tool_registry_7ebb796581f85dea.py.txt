# mutation-pin: TREQ_TOOL_REGISTRY 7ebb796581f85dea
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router._internal.capabilities.tools import ToolRegistry

pytestmark = pytest.mark.verification_kind("unit")


def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


@pytest.mark.verifies("TREQ_TOOL_REGISTRY[revision==1]")
def test_get_unregistered_tool_raises_key_error() -> None:
    registry = ToolRegistry.from_tools([add])
    with pytest.raises(KeyError, match=r"Unknown tool: lookup_weather\."):
        registry.get("lookup_weather")

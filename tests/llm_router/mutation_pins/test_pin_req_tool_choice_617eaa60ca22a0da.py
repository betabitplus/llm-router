# mutation-pin: REQ_TOOL_CHOICE 617eaa60ca22a0da
# pinned-by: claude-opus-5-5: With the mutant, choice=None raises TypeError and "auto" falls into the named-tool string branch. Every call that leaves tool_choice unset would fail, and the reserved keyword would be treated as an explicit tool name. Named-choice normalization only works if keywords are kept apart from tool names
from __future__ import annotations

import pytest

from llm_router._internal.capabilities.tools import (
    ToolChoice,
    ToolRegistry,
    normalize_tool_choice,
)

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_TOOL_CHOICE[revision==1]")
def test_normalize_tool_choice_auto_and_named() -> None:
    def add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    registry: ToolRegistry | None = None
    try:
        reg = ToolRegistry()
        if hasattr(reg, "register"):
            reg.register(add)
            registry = reg
        elif hasattr(reg, "add"):
            reg.add(add)
            registry = reg
        elif hasattr(reg, "register_tool"):
            reg.register_tool(add)
            registry = reg
    except Exception:
        try:
            registry = ToolRegistry([add])  # type: ignore[arg-type]
        except Exception:
            registry = None

    choice_none = normalize_tool_choice(None)
    assert choice_none == ToolChoice(kind="auto")
    assert choice_none.kind == "auto"

    choice_none_with_reg = normalize_tool_choice(None, registry=registry)
    assert choice_none_with_reg == ToolChoice(kind="auto")
    assert choice_none_with_reg.kind == "auto"

    choice_auto = normalize_tool_choice("auto")
    assert choice_auto == ToolChoice(kind="auto")
    assert choice_auto.kind == "auto"

    choice_auto_with_reg = normalize_tool_choice("auto", registry=registry)
    assert choice_auto_with_reg == ToolChoice(kind="auto")
    assert choice_auto_with_reg.kind == "auto"

    choice_named = normalize_tool_choice("add", registry=registry)
    assert choice_named.kind == "named"
    assert choice_named.name == "add"

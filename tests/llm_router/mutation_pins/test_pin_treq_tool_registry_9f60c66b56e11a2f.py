# mutation-pin: TREQ_TOOL_REGISTRY 9f60c66b56e11a2f
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router._internal.capabilities.tools import ToolRegistry

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_TOOL_REGISTRY[revision==1]")
def test_default_registry_is_empty_with_fresh_mapping() -> None:
    first = ToolRegistry()
    second = ToolRegistry()

    assert len(first.tools) == 0
    assert list(first.tools) == []
    assert first.tools is not second.tools
    with pytest.raises(KeyError):
        first.get("missing")

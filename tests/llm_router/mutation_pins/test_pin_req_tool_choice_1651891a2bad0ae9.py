# mutation-pin: REQ_TOOL_CHOICE 1651891a2bad0ae9
# pinned-by: claude-opus-5-5: The mutant drops the registry check for the string form only. A bare string naming an unregistered tool is now accepted as a named choice, while the mapping form still raises KeyError. That breaks the criterion that both public named-choice forms resolve to the same registered tool, and it lets an u
from __future__ import annotations

import pytest

from llm_router._internal.capabilities.tools import ToolRegistry, normalize_tool_choice

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_TOOL_CHOICE[revision==1]")
def test_normalize_tool_choice_named_string_missing_from_registry_raises_key_error() -> None:
    registry = ToolRegistry()
    missing_tool_name = "fetch_weather"

    with pytest.raises(KeyError):
        normalize_tool_choice(missing_tool_name, registry=registry)

# mutation-pin: TREQ_CONFIG_TOOL_ROUND_LIMIT c18833e1526efa72
# pinned-by: claude-opus-5-5
from __future__ import annotations

from dataclasses import replace

import pytest

from llm_router._api.errors import ConfigurationError
from llm_router._internal.config import build_default_config, validate_config

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_CONFIG_TOOL_ROUND_LIMIT[revision==1]")
def test_validation_boundary_for_default_tool_rounds() -> None:
    config = build_default_config()

    accepted_defaults = replace(config.defaults, default_max_tool_rounds=1)
    accepted_config = replace(config, defaults=accepted_defaults)

    validate_config(accepted_config)

    rejected_defaults = replace(config.defaults, default_max_tool_rounds=0)
    rejected_config = replace(config, defaults=rejected_defaults)

    with pytest.raises(ConfigurationError, match=r"default max tool rounds"):
        validate_config(rejected_config)

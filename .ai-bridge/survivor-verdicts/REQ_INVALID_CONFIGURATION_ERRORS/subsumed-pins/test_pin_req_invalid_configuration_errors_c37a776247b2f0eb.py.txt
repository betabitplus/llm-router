# mutation-pin: REQ_INVALID_CONFIGURATION_ERRORS c37a776247b2f0eb
# pinned-by: claude-opus-5-5
from __future__ import annotations

from dataclasses import replace

import pytest

from llm_router import ConfigurationError
from llm_router._internal.config import build_default_config, validate_config

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_INVALID_CONFIGURATION_ERRORS[revision==2]")
def test_validate_config_boundary_for_default_max_tool_rounds() -> None:
    config = build_default_config()

    valid_config = replace(
        config, defaults=replace(config.defaults, default_max_tool_rounds=1)
    )
    validate_config(valid_config)

    invalid_config = replace(
        config, defaults=replace(config.defaults, default_max_tool_rounds=0)
    )
    with pytest.raises(ConfigurationError, match="default max tool rounds"):
        validate_config(invalid_config)

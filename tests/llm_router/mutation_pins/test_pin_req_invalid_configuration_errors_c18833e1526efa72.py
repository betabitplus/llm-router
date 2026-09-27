# mutation-pin: REQ_INVALID_CONFIGURATION_ERRORS c18833e1526efa72
# pinned-by: claude-opus-5-5
from __future__ import annotations

from dataclasses import replace

import pytest

from llm_router import ConfigurationError
from llm_router._internal.config import build_default_config, validate_config

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_INVALID_CONFIGURATION_ERRORS[revision==2]")
def test_validation_accepts_default_max_tool_rounds_of_one() -> None:
    config = build_default_config()

    valid_config = replace(
        config,
        defaults=replace(config.defaults, default_max_tool_rounds=1),
    )
    validate_config(valid_config)

    invalid_config = replace(
        config,
        defaults=replace(config.defaults, default_max_tool_rounds=0),
    )
    with pytest.raises(ConfigurationError, match="default max tool rounds"):
        validate_config(invalid_config)

# mutation-pin: REQ_INVALID_CONFIGURATION_ERRORS c18833e1526efa72
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

from dataclasses import replace

import pytest

from llm_router import ConfigurationError, get_config, install_config

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_INVALID_CONFIGURATION_ERRORS[revision==2]")
def test_install_accepts_one_tool_round_and_rejects_zero() -> None:
    original = get_config()
    config = original

    valid = replace(
        config, defaults=replace(config.defaults, default_max_tool_rounds=1)
    )
    installed = install_config(valid)
    assert installed.default_max_tool_rounds == 1

    invalid = replace(
        config, defaults=replace(config.defaults, default_max_tool_rounds=0)
    )
    with pytest.raises(ConfigurationError, match=r"^default max tool rounds"):
        install_config(invalid)
    assert get_config().default_max_tool_rounds == 1

    install_config(original)

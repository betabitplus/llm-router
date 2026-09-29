# mutation-pin: TREQ_CONFIG_TOOL_ROUND_LIMIT c37a776247b2f0eb
# pinned-by: claude-opus-5-5
from __future__ import annotations

from dataclasses import replace

import pytest

from llm_router import ConfigurationError
from llm_router._internal.config import build_default_config, validate_config

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_CONFIG_TOOL_ROUND_LIMIT[revision==1]")
def test_tool_round_limit_boundary_is_one() -> None:
    config = build_default_config()

    accepted = replace(config.defaults, default_max_tool_rounds=1)
    assert validate_config(replace(config, defaults=accepted)) is None

    rejected = replace(config.defaults, default_max_tool_rounds=0)
    with pytest.raises(ConfigurationError, match=r"default max tool rounds"):
        validate_config(replace(config, defaults=rejected))

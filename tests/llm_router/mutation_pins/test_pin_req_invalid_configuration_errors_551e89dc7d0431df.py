# mutation-pin: REQ_INVALID_CONFIGURATION_ERRORS 551e89dc7d0431df
# pinned-by: claude-opus-5-5
from __future__ import annotations

from dataclasses import replace

import pytest

from llm_router import ConfigurationError
from llm_router._internal.config import build_default_config, validate_config

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_INVALID_CONFIGURATION_ERRORS[revision==2]")
def test_validation_accepts_one_min_route_for_fallback_shuffle() -> None:
    config = build_default_config()
    defaults = replace(
        config.defaults,
        policy=replace(config.defaults.policy, min_routes_for_fallback_shuffle=1),
    )
    validate_config(replace(config, defaults=defaults))

    invalid_defaults = replace(
        config.defaults,
        policy=replace(config.defaults.policy, min_routes_for_fallback_shuffle=0),
    )
    with pytest.raises(ConfigurationError, match="minimum routes for fallback shuffle"):
        validate_config(replace(config, defaults=invalid_defaults))

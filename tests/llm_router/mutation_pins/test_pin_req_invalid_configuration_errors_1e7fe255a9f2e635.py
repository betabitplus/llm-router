# mutation-pin: REQ_INVALID_CONFIGURATION_ERRORS 1e7fe255a9f2e635
# pinned-by: claude-opus-5-5
from __future__ import annotations

from dataclasses import replace

import pytest

from llm_router import ConfigurationError
from llm_router._internal.config import build_default_config, validate_config

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_INVALID_CONFIGURATION_ERRORS[revision==2]")
def test_validate_config_min_routes_for_fallback_shuffle_boundary() -> None:
    config = build_default_config()

    valid_policy = replace(config.defaults.policy, min_routes_for_fallback_shuffle=1)
    valid_defaults = replace(config.defaults, policy=valid_policy)
    validate_config(replace(config, defaults=valid_defaults))

    invalid_policy = replace(config.defaults.policy, min_routes_for_fallback_shuffle=0)
    invalid_defaults = replace(config.defaults, policy=invalid_policy)
    with pytest.raises(ConfigurationError, match="minimum routes for fallback shuffle"):
        validate_config(replace(config, defaults=invalid_defaults))

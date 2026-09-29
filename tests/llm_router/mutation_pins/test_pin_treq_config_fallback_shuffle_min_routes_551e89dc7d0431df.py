# mutation-pin: TREQ_CONFIG_FALLBACK_SHUFFLE_MIN_ROUTES 551e89dc7d0431df
# pinned-by: claude-opus-5-5
from __future__ import annotations

from dataclasses import replace

import pytest

from llm_router import ConfigurationError
from llm_router._internal.config import build_default_config, validate_config

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_CONFIG_FALLBACK_SHUFFLE_MIN_ROUTES[revision==1]")
def test_fallback_shuffle_minimum_boundary_accepts_one_rejects_zero() -> None:
    config = build_default_config()

    valid_policy = replace(config.policy, min_routes_for_fallback_shuffle=1)
    valid_defaults = replace(config.defaults, policy=valid_policy)
    valid_config = replace(config, defaults=valid_defaults)

    assert validate_config(valid_config) is None

    invalid_policy = replace(config.policy, min_routes_for_fallback_shuffle=0)
    invalid_defaults = replace(config.defaults, policy=invalid_policy)
    invalid_config = replace(config, defaults=invalid_defaults)

    with pytest.raises(ConfigurationError, match=r"minimum routes"):
        validate_config(invalid_config)

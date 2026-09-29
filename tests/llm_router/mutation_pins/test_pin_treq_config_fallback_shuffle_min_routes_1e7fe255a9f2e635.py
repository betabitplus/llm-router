# mutation-pin: TREQ_CONFIG_FALLBACK_SHUFFLE_MIN_ROUTES 1e7fe255a9f2e635
# pinned-by: claude-opus-5-5
from __future__ import annotations

from dataclasses import replace

import pytest

from llm_router import ConfigurationError
from llm_router._internal.config import build_default_config, validate_config

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_CONFIG_FALLBACK_SHUFFLE_MIN_ROUTES[revision==1]")
def test_validation_accepts_one_fallback_shuffle_minimum() -> None:
    config = build_default_config()
    policy = replace(config.policy, min_routes_for_fallback_shuffle=1)
    valid_config = replace(config, defaults=replace(config.defaults, policy=policy))

    assert validate_config(valid_config) is None


@pytest.mark.verifies("TREQ_CONFIG_FALLBACK_SHUFFLE_MIN_ROUTES[revision==1]")
def test_validation_rejects_zero_fallback_shuffle_minimum() -> None:
    config = build_default_config()
    policy = replace(config.policy, min_routes_for_fallback_shuffle=0)
    invalid_config = replace(config, defaults=replace(config.defaults, policy=policy))

    with pytest.raises(ConfigurationError, match="minimum routes"):
        validate_config(invalid_config)

# mutation-pin: TREQ_CONFIG_ROUTE_ATTEMPT_LIMIT 4a11c78df0078b1f
# pinned-by: claude-opus-5-5
# tests/llm_router/unit/test_config_route_attempt_limit_boundary.py
from __future__ import annotations

from dataclasses import replace

import pytest

from llm_router import ConfigurationError
from llm_router._internal.config import build_default_config, validate_config

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_CONFIG_ROUTE_ATTEMPT_LIMIT[revision==1]")
def test_validation_accepts_route_attempt_limit_of_one() -> None:
    config = build_default_config()
    policy = replace(config.policy, max_attempts=1)
    valid_config = replace(config, defaults=replace(config.defaults, policy=policy))

    assert validate_config(valid_config) is None


@pytest.mark.verifies("TREQ_CONFIG_ROUTE_ATTEMPT_LIMIT[revision==1]")
def test_validation_rejects_route_attempt_limit_of_zero() -> None:
    config = build_default_config()
    policy = replace(config.policy, max_attempts=0)
    invalid_config = replace(config, defaults=replace(config.defaults, policy=policy))

    with pytest.raises(ConfigurationError, match="policy max attempts"):
        validate_config(invalid_config)

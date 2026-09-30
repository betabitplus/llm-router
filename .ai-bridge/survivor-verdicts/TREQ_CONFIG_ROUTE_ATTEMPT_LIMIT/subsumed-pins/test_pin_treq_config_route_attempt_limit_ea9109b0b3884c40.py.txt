# mutation-pin: TREQ_CONFIG_ROUTE_ATTEMPT_LIMIT ea9109b0b3884c40
# pinned-by: claude-opus-5-5
from __future__ import annotations

from dataclasses import replace

import pytest

from llm_router._api.errors import ConfigurationError
from llm_router._internal.config import build_default_config
from llm_router._internal.config.validation import validate_config

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_CONFIG_ROUTE_ATTEMPT_LIMIT[revision==1]")
def test_route_attempt_limit_boundary_accepts_one_rejects_zero() -> None:
    config = build_default_config()

    policy_one = replace(config.policy, max_attempts=1)
    config_one = replace(config, defaults=replace(config.defaults, policy=policy_one))
    validate_config(config_one)

    policy_zero = replace(config.policy, max_attempts=0)
    config_zero = replace(config, defaults=replace(config.defaults, policy=policy_zero))
    with pytest.raises(ConfigurationError, match=r"policy max attempts"):
        validate_config(config_zero)

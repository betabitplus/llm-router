# mutation-pin: TREQ_CONFIG_ATTEMPT_TIMEOUT b6340db1c7f8750a
# pinned-by: claude-opus-5-5
from __future__ import annotations

from dataclasses import replace

import pytest

from llm_router import ConfigurationError
from llm_router._internal.config import build_default_config, validate_config

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_CONFIG_ATTEMPT_TIMEOUT[revision==1]")
def test_validate_config_allows_disabled_attempt_timeout() -> None:
    config = build_default_config()
    policy = replace(config.policy, attempt_timeout_seconds=None)
    defaults = replace(config.defaults, policy=policy)
    valid_config = replace(config, defaults=defaults)

    validate_config(valid_config)


@pytest.mark.verifies("TREQ_CONFIG_ATTEMPT_TIMEOUT[revision==1]")
def test_validate_config_still_checks_later_rule_when_timeout_disabled() -> None:
    config = build_default_config()
    policy = replace(
        config.policy,
        attempt_timeout_seconds=None,
        min_routes_for_fallback_shuffle=0,
    )
    defaults = replace(config.defaults, policy=policy)
    invalid_config = replace(config, defaults=defaults)

    with pytest.raises(ConfigurationError, match=r"minimum routes"):
        validate_config(invalid_config)

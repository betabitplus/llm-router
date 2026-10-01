# mutation-pin: TREQ_CONFIG_ATTEMPT_TIMEOUT FN-8B04992A
# pinned-by: delegate, one pin for 2 pins of validate_config
# kills: 3b57c08f839ab791 b6340db1c7f8750a
from __future__ import annotations

from dataclasses import replace

import pytest

from llm_router import ConfigurationError
from llm_router._internal.config import build_default_config
from llm_router._internal.config.validation import validate_config

pytestmark = pytest.mark.verification_kind("unit")


def _with_policy(**changes):
    config = build_default_config()
    policy = replace(config.policy, **changes)
    defaults = replace(config.defaults, policy=policy)
    return replace(config, defaults=defaults)


@pytest.mark.verifies("TREQ_CONFIG_ATTEMPT_TIMEOUT[revision==1]")
def test_attempt_timeout_must_be_positive_or_disabled() -> None:
    assert validate_config(_with_policy(attempt_timeout_seconds=0.5)) is None
    assert validate_config(_with_policy(attempt_timeout_seconds=None)) is None

    with pytest.raises(ConfigurationError, match=r"attempt timeout"):
        validate_config(_with_policy(attempt_timeout_seconds=0))

    with pytest.raises(ConfigurationError, match=r"attempt timeout"):
        validate_config(_with_policy(attempt_timeout_seconds=-0.5))

    with pytest.raises(ConfigurationError, match=r"minimum routes"):
        validate_config(
            _with_policy(
                attempt_timeout_seconds=None,
                min_routes_for_fallback_shuffle=0,
            )
        )

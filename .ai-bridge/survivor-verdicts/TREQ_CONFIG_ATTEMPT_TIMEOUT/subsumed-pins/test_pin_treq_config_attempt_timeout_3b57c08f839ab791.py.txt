# mutation-pin: TREQ_CONFIG_ATTEMPT_TIMEOUT 3b57c08f839ab791
# pinned-by: claude-opus-5-5
from __future__ import annotations

from dataclasses import replace

import pytest

from llm_router import ConfigurationError
from llm_router._internal.config import build_default_config
from llm_router._internal.config.validation import validate_config

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_CONFIG_ATTEMPT_TIMEOUT[revision==1]")
def test_attempt_timeout_boundary_accepts_fraction_rejects_nonpositive() -> None:
    config = build_default_config()

    fractional_policy = replace(config.policy, attempt_timeout_seconds=0.5)
    fractional_defaults = replace(config.defaults, policy=fractional_policy)
    fractional_config = replace(config, defaults=fractional_defaults)

    assert validate_config(fractional_config) is None

    zero_policy = replace(config.policy, attempt_timeout_seconds=0)
    zero_defaults = replace(config.defaults, policy=zero_policy)
    zero_config = replace(config, defaults=zero_defaults)

    with pytest.raises(ConfigurationError, match=r"attempt timeout"):
        validate_config(zero_config)

    negative_policy = replace(config.policy, attempt_timeout_seconds=-0.5)
    negative_defaults = replace(config.defaults, policy=negative_policy)
    negative_config = replace(config, defaults=negative_defaults)

    with pytest.raises(ConfigurationError, match=r"attempt timeout"):
        validate_config(negative_config)

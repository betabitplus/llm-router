# mutation-pin: REQ_INVALID_CONFIGURATION_ERRORS 4a11c78df0078b1f
# pinned-by: claude-opus-5-5
from __future__ import annotations

from dataclasses import replace

import pytest

from llm_router import ConfigurationError
from llm_router._internal.config import build_default_config, validate_config

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_INVALID_CONFIGURATION_ERRORS[revision==2]")
def test_validation_policy_max_attempts_boundary() -> None:
    config = build_default_config()

    valid_policy = replace(config.defaults.policy, max_attempts=1)
    valid_defaults = replace(config.defaults, policy=valid_policy)
    valid_config = replace(config, defaults=valid_defaults)
    validate_config(valid_config)

    invalid_policy = replace(config.defaults.policy, max_attempts=0)
    invalid_defaults = replace(config.defaults, policy=invalid_policy)
    invalid_config = replace(config, defaults=invalid_defaults)
    with pytest.raises(ConfigurationError, match="policy max attempts"):
        validate_config(invalid_config)

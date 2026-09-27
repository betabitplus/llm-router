# mutation-pin: REQ_INVALID_CONFIGURATION_ERRORS 3b57c08f839ab791
# pinned-by: claude-opus-5-5: The documented constraint is that the policy attempt timeout must be greater than 0. The mutant moves that limit to greater than 1, so a valid configuration with a timeout of 1.0 (or 0.5) now fails with ConfigurationError. Only configurations that actually break a constraint should be rejected, so t
from __future__ import annotations

from dataclasses import replace

import pytest

from llm_router import ConfigurationError
from llm_router._internal.config import build_default_config, validate_config

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_INVALID_CONFIGURATION_ERRORS[revision==2]")
def test_validation_accepts_one_second_policy_attempt_timeout() -> None:
    config = build_default_config()

    valid_policy = replace(config.defaults.policy, attempt_timeout_seconds=1.0)
    valid_config = replace(config, defaults=replace(config.defaults, policy=valid_policy))
    validate_config(valid_config)

    invalid_policy = replace(config.defaults.policy, attempt_timeout_seconds=0.0)
    invalid_config = replace(config, defaults=replace(config.defaults, policy=invalid_policy))
    with pytest.raises(ConfigurationError, match="policy attempt timeout"):
        validate_config(invalid_config)

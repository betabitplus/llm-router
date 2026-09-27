# mutation-pin: REQ_INVALID_CONFIGURATION_ERRORS ea9109b0b3884c40
# pinned-by: claude-opus-5-5: The constraint is policy max_attempts >= 1, but the mutant turns it into > 1. That makes a ConfigurationError fire for the valid boundary value 1, and execution has confirmed this. The requirement only permits rejecting configurations that actually break a constraint, so moving the boundary breaks w
from __future__ import annotations

from dataclasses import replace

import pytest
from llm_router import ConfigurationError
from llm_router._internal.config import build_default_config, validate_config

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_INVALID_CONFIGURATION_ERRORS[revision==2]")
def test_validation_accepts_single_attempt_policy_and_rejects_zero() -> None:
    config = build_default_config()

    valid_policy = replace(config.defaults.policy, max_attempts=1)
    valid_config = replace(config, defaults=replace(config.defaults, policy=valid_policy))
    validate_config(valid_config)

    invalid_policy = replace(config.defaults.policy, max_attempts=0)
    invalid_config = replace(config, defaults=replace(config.defaults, policy=invalid_policy))
    with pytest.raises(ConfigurationError, match="policy max attempts must be at least 1"):
        validate_config(invalid_config)

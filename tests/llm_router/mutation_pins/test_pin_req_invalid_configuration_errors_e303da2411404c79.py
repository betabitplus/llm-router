# mutation-pin: REQ_INVALID_CONFIGURATION_ERRORS e303da2411404c79
# pinned-by: claude-opus-5-5: The constraint is that the retry minimum wait must be greater than 0, as its own error message says. The mutant changes the check to greater than 1, so a valid configuration with min_wait_seconds=0.5 now raises ConfigurationError. Execution confirmed this. The requirement is to reject only configura
from __future__ import annotations

from dataclasses import replace

import pytest

from llm_router import ConfigurationError
from llm_router._internal.config import build_default_config, validate_config

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_INVALID_CONFIGURATION_ERRORS[revision==2]")
def test_validation_accepts_subsecond_min_wait_and_rejects_zero() -> None:
    config = build_default_config()

    valid_retry = replace(config.defaults.retry_policy, min_wait_seconds=0.5)
    valid_defaults = replace(config.defaults, retry_policy=valid_retry)
    validate_config(replace(config, defaults=valid_defaults))

    invalid_retry = replace(config.defaults.retry_policy, min_wait_seconds=0.0)
    invalid_defaults = replace(config.defaults, retry_policy=invalid_retry)
    with pytest.raises(ConfigurationError, match="retry min wait must be greater than 0"):
        validate_config(replace(config, defaults=invalid_defaults))

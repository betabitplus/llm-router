# mutation-pin: REQ_INVALID_CONFIGURATION_ERRORS a6c77976ba2d4065
# pinned-by: claude-opus-5-5: The documented constraint is that retry max attempts must be at least 1. The mutant moves that boundary to 2, so a valid configuration with max_attempts=1 now raises ConfigurationError, which a run confirmed. The requirement says to reject only configurations that break an applicable constraint, so
from __future__ import annotations

from dataclasses import replace
import pytest
from llm_router import ConfigurationError
from llm_router._internal.config import build_default_config, validate_config

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_INVALID_CONFIGURATION_ERRORS[revision==2]")
def test_validation_permits_retry_max_attempts_of_one() -> None:
    config = build_default_config()

    valid_retry = replace(config.retry_policy, max_attempts=1)
    valid_defaults = replace(config.defaults, retry_policy=valid_retry)
    validate_config(replace(config, defaults=valid_defaults))

    invalid_retry = replace(config.retry_policy, max_attempts=0)
    invalid_defaults = replace(config.defaults, retry_policy=invalid_retry)
    with pytest.raises(ConfigurationError, match="retry max attempts"):
        validate_config(replace(config, defaults=invalid_defaults))

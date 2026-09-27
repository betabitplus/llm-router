# mutation-pin: REQ_INVALID_CONFIGURATION_ERRORS a02b9c41521c0e84
# pinned-by: claude-opus-5-5: The constraint is that retry max attempts must be at least 1, and the error message says so. The requirement only rejects configurations that break a constraint. The mutant also rejects the valid boundary value max_attempts=1 with ConfigurationError (confirmed by running it), so a correctly configur
from __future__ import annotations

from dataclasses import replace

import pytest

from llm_router import ConfigurationError
from llm_router._internal.config import build_default_config, validate_config

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_INVALID_CONFIGURATION_ERRORS[revision==2]")
def test_retry_policy_max_attempts_boundary() -> None:
    config = build_default_config()

    boundary_retry = replace(config.defaults.retry_policy, max_attempts=1)
    boundary_defaults = replace(config.defaults, retry_policy=boundary_retry)
    validate_config(replace(config, defaults=boundary_defaults))

    invalid_retry = replace(config.defaults.retry_policy, max_attempts=0)
    invalid_defaults = replace(config.defaults, retry_policy=invalid_retry)
    with pytest.raises(ConfigurationError, match="retry max attempts must be at least 1"):
        validate_config(replace(config, defaults=invalid_defaults))

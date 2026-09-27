# mutation-pin: REQ_INVALID_CONFIGURATION_ERRORS 19ce8cfa2ea55f04
# pinned-by: claude-opus-5-5: The requirement only calls for rejecting configurations that break a configuration constraint, and that constraint is max_wait >= min_wait. The mutant also rejects the valid case where max_wait equals min_wait. Execution confirmed it: the mutant raises ConfigurationError on a valid config that the o
from __future__ import annotations

from dataclasses import replace

import pytest

from llm_router import ConfigurationError
from llm_router._internal.config import build_default_config, validate_config

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_INVALID_CONFIGURATION_ERRORS[revision==2]")
def test_validation_allows_equal_retry_min_and_max_wait() -> None:
    config = build_default_config()
    equal_wait_retry = replace(
        config.defaults.retry_policy,
        min_wait_seconds=1.0,
        max_wait_seconds=1.0,
    )
    valid_config = replace(
        config,
        defaults=replace(config.defaults, retry_policy=equal_wait_retry),
    )

    validate_config(valid_config)

    invalid_wait_retry = replace(
        config.defaults.retry_policy,
        min_wait_seconds=2.0,
        max_wait_seconds=1.0,
    )
    invalid_config = replace(
        config,
        defaults=replace(config.defaults, retry_policy=invalid_wait_retry),
    )

    with pytest.raises(ConfigurationError, match="retry max wait is invalid"):
        validate_config(invalid_config)

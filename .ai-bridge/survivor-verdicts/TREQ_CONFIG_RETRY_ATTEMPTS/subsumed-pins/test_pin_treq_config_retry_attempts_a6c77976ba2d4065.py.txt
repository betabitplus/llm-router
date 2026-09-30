# mutation-pin: TREQ_CONFIG_RETRY_ATTEMPTS a6c77976ba2d4065
# pinned-by: claude-opus-5-5
from __future__ import annotations

from dataclasses import replace

import pytest

from llm_router._api.errors import ConfigurationError
from llm_router._internal.config import build_default_config, validate_config

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_CONFIG_RETRY_ATTEMPTS[revision==1]")
def test_retry_max_attempts_boundary_of_one() -> None:
    config = build_default_config()

    one_attempt_retry = replace(config.retry_policy, max_attempts=1)
    one_attempt_defaults = replace(config.defaults, retry_policy=one_attempt_retry)
    one_attempt_config = replace(config, defaults=one_attempt_defaults)

    validate_config(one_attempt_config)

    zero_attempt_retry = replace(config.retry_policy, max_attempts=0)
    zero_attempt_defaults = replace(config.defaults, retry_policy=zero_attempt_retry)
    zero_attempt_config = replace(config, defaults=zero_attempt_defaults)

    with pytest.raises(ConfigurationError, match=r"retry max attempts"):
        validate_config(zero_attempt_config)

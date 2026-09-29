# mutation-pin: TREQ_CONFIG_RETRY_ATTEMPTS a02b9c41521c0e84
# pinned-by: claude-opus-5-5
from __future__ import annotations

from dataclasses import replace

import pytest

from llm_router import ConfigurationError
from llm_router._internal.config import build_default_config, validate_config

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_CONFIG_RETRY_ATTEMPTS[revision==1]")
def test_validate_config_accepts_one_retry_attempt_rejects_zero() -> None:
    config = build_default_config()

    one_retry = replace(config.retry_policy, max_attempts=1)
    one_defaults = replace(config.defaults, retry_policy=one_retry)
    one_config = replace(config, defaults=one_defaults)

    assert validate_config(one_config) is None

    zero_retry = replace(config.retry_policy, max_attempts=0)
    zero_defaults = replace(config.defaults, retry_policy=zero_retry)
    zero_config = replace(config, defaults=zero_defaults)

    with pytest.raises(ConfigurationError, match=r"retry max attempts"):
        validate_config(zero_config)

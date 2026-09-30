# mutation-pin: TREQ_CONFIG_RETRY_WAIT_BOUNDS e303da2411404c79
# pinned-by: claude-opus-5-5
from __future__ import annotations

from dataclasses import replace

import pytest

from llm_router._api.errors import ConfigurationError
from llm_router._internal.config import build_default_config, validate_config

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_CONFIG_RETRY_WAIT_BOUNDS[revision==1]")
def test_validation_accepts_min_wait_strictly_above_zero() -> None:
    config = build_default_config()
    retry = replace(
        config.retry_policy,
        min_wait_seconds=0.5,
        max_wait_seconds=1.0,
    )
    valid_config = replace(
        config, defaults=replace(config.defaults, retry_policy=retry)
    )

    assert validate_config(valid_config) is None


@pytest.mark.verifies("TREQ_CONFIG_RETRY_WAIT_BOUNDS[revision==1]")
def test_validation_rejects_non_positive_min_wait() -> None:
    config = build_default_config()
    retry = replace(
        config.retry_policy,
        min_wait_seconds=0.0,
        max_wait_seconds=1.0,
    )
    invalid_config = replace(
        config, defaults=replace(config.defaults, retry_policy=retry)
    )

    with pytest.raises(ConfigurationError, match=r"retry min wait"):
        validate_config(invalid_config)

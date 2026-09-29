# mutation-pin: TREQ_CONFIG_RETRY_WAIT_BOUNDS 19ce8cfa2ea55f04
# pinned-by: claude-opus-5-5
from __future__ import annotations

from dataclasses import replace

import pytest

from llm_router import ConfigurationError
from llm_router._internal.config import build_default_config, validate_config

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_CONFIG_RETRY_WAIT_BOUNDS[revision==1]")
def test_validate_config_accepts_equal_retry_wait_bounds() -> None:
    config = build_default_config()
    retry = replace(
        config.retry_policy,
        min_wait_seconds=1.0,
        max_wait_seconds=1.0,
    )
    valid_config = replace(
        config, defaults=replace(config.defaults, retry_policy=retry)
    )

    assert validate_config(valid_config) is None


@pytest.mark.verifies("TREQ_CONFIG_RETRY_WAIT_BOUNDS[revision==1]")
def test_validate_config_rejects_max_wait_below_min_wait() -> None:
    config = build_default_config()
    retry = replace(
        config.retry_policy,
        min_wait_seconds=2.0,
        max_wait_seconds=1.0,
    )
    invalid_config = replace(
        config, defaults=replace(config.defaults, retry_policy=retry)
    )

    with pytest.raises(ConfigurationError, match=r"retry max wait"):
        validate_config(invalid_config)

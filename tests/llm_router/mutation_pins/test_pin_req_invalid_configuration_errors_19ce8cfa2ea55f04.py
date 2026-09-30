# mutation-pin: REQ_INVALID_CONFIGURATION_ERRORS 19ce8cfa2ea55f04
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

from dataclasses import replace

import pytest

from llm_router import (
    ConfigurationError,
    LLMRouterConfig,
    get_config,
    install_config,
)

pytestmark = pytest.mark.verification_kind("unit")


def _with_waits(
    config: LLMRouterConfig, min_wait: float, max_wait: float
) -> LLMRouterConfig:
    retry = replace(
        config.defaults.retry_policy,
        min_wait_seconds=min_wait,
        max_wait_seconds=max_wait,
    )
    return replace(config, defaults=replace(config.defaults, retry_policy=retry))


@pytest.mark.verifies("REQ_INVALID_CONFIGURATION_ERRORS[revision==2]")
def test_retry_max_wait_equal_to_min_allowed_and_below_rejected() -> None:
    original = get_config()
    invalid = _with_waits(original, 2.0, 1.0)
    with pytest.raises(ConfigurationError, match=r"^retry max wait is invalid\.$"):
        install_config(invalid)

    equal = _with_waits(original, 1.0, 1.0)
    assert install_config(equal) is equal
    install_config(original)

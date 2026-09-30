# mutation-pin: REQ_INVALID_CONFIGURATION_ERRORS 3b57c08f839ab791
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

from dataclasses import replace

import pytest

from llm_router import ConfigurationError, LLMRouterConfig, get_config, install_config

pytestmark = pytest.mark.verification_kind("unit")


def _with_timeout(base: LLMRouterConfig, timeout: float) -> LLMRouterConfig:
    policy = replace(base.defaults.policy, attempt_timeout_seconds=timeout)
    return replace(base, defaults=replace(base.defaults, policy=policy))


@pytest.mark.verifies("REQ_INVALID_CONFIGURATION_ERRORS[revision==2]")
def test_attempt_timeout_accepts_subsecond_and_rejects_zero() -> None:
    base = get_config()

    with pytest.raises(ConfigurationError, match=r"^policy attempt timeout"):
        install_config(_with_timeout(base, 0.0))

    installed = install_config(_with_timeout(base, 0.5))
    install_config(base)
    assert installed.policy.attempt_timeout_seconds == 0.5

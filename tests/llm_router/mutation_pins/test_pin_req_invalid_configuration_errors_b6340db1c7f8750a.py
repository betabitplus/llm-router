# mutation-pin: REQ_INVALID_CONFIGURATION_ERRORS b6340db1c7f8750a
# pinned-by: claude-opus-5-5
from __future__ import annotations

from dataclasses import replace

import pytest

from llm_router import ConfigurationError
from llm_router._internal.config import build_default_config, validate_config

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_INVALID_CONFIGURATION_ERRORS[revision==2]")
def test_invalid_config_with_no_attempt_timeout_raises_configuration_error() -> None:
    config = build_default_config()
    policy = replace(config.defaults.policy, attempt_timeout_seconds=None)
    defaults = replace(
        config.defaults,
        policy=policy,
        structured_output_max_attempts=0,
    )

    with pytest.raises(ConfigurationError, match=r"structured output max attempts"):
        validate_config(replace(config, defaults=defaults))

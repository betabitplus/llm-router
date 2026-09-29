# mutation-pin: TREQ_CONFIG_STRUCTURED_OUTPUT_ATTEMPTS 43c47ed5eb7d2a63
# pinned-by: claude-opus-5-5
from __future__ import annotations

from dataclasses import replace

import pytest

from llm_router import ConfigurationError
from llm_router._internal.config import build_default_config, validate_config

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_CONFIG_STRUCTURED_OUTPUT_ATTEMPTS[revision==1]")
def test_validation_accepts_one_structured_output_attempt() -> None:
    config = build_default_config()
    defaults = replace(config.defaults, structured_output_max_attempts=1)

    assert validate_config(replace(config, defaults=defaults)) is None


@pytest.mark.verifies("TREQ_CONFIG_STRUCTURED_OUTPUT_ATTEMPTS[revision==1]")
def test_validation_rejects_zero_structured_output_attempts() -> None:
    config = build_default_config()
    defaults = replace(config.defaults, structured_output_max_attempts=0)

    with pytest.raises(ConfigurationError, match="structured output max attempts"):
        validate_config(replace(config, defaults=defaults))

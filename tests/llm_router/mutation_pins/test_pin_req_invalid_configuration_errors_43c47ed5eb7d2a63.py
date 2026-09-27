# mutation-pin: REQ_INVALID_CONFIGURATION_ERRORS 43c47ed5eb7d2a63
# pinned-by: claude-opus-5-5: The mutant moves the structured-output-attempts constraint from >=1 to >=2, so a valid configuration with a single attempt now fails with ConfigurationError. The requirement ties rejection to actual constraint violations, and its own error message still says "at least 1", so this is a real regressio
from __future__ import annotations

from dataclasses import replace

import pytest

from llm_router import ConfigurationError
from llm_router._internal.config import build_default_config, validate_config

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_INVALID_CONFIGURATION_ERRORS[revision==2]")
def test_structured_output_max_attempts_boundary() -> None:
    config = build_default_config()

    valid_defaults = replace(config.defaults, structured_output_max_attempts=1)
    validate_config(replace(config, defaults=valid_defaults))

    invalid_defaults = replace(config.defaults, structured_output_max_attempts=0)
    with pytest.raises(ConfigurationError, match="structured output max attempts"):
        validate_config(replace(config, defaults=invalid_defaults))

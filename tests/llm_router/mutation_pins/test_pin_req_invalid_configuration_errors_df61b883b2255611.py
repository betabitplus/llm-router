# mutation-pin: REQ_INVALID_CONFIGURATION_ERRORS df61b883b2255611
# pinned-by: claude-opus-5-5: The constraint is "structured output max attempts must be at least 1". The mutant rejects the valid boundary value 1 with a ConfigurationError, so it fails a configuration that breaks no constraint. That shifts the boundary the requirement's rejection is defined by, and a valid public request would
from __future__ import annotations

from dataclasses import replace

import pytest

from llm_router import ConfigurationError
from llm_router._internal.config import build_default_config, validate_config

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_INVALID_CONFIGURATION_ERRORS[revision==2]")
def test_validation_accepts_one_structured_output_attempt_and_rejects_zero() -> None:
    config = build_default_config()

    valid_defaults = replace(config.defaults, structured_output_max_attempts=1)
    validate_config(replace(config, defaults=valid_defaults))

    invalid_defaults = replace(config.defaults, structured_output_max_attempts=0)
    with pytest.raises(ConfigurationError, match="structured output max attempts"):
        validate_config(replace(config, defaults=invalid_defaults))

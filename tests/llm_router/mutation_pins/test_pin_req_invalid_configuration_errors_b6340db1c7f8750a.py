# mutation-pin: REQ_INVALID_CONFIGURATION_ERRORS b6340db1c7f8750a
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

from dataclasses import replace

import pytest

import llm_router as package

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_INVALID_CONFIGURATION_ERRORS[revision==2]")
def test_config_without_timeout_rejects_invalid_structured_attempts() -> None:
    current = package.get_config()
    policy = replace(current.defaults.policy, attempt_timeout_seconds=None)
    defaults = replace(
        current.defaults,
        policy=policy,
        structured_output_max_attempts=0,
    )
    invalid_config = replace(current, defaults=defaults)

    with pytest.raises(
        package.ConfigurationError,
        match=r"^structured output max attempts must be at least 1\.$",
    ):
        package.install_config(invalid_config)

    assert package.get_config() is current

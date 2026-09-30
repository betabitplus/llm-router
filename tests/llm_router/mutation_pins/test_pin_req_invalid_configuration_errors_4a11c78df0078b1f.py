# mutation-pin: REQ_INVALID_CONFIGURATION_ERRORS 4a11c78df0078b1f
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

from dataclasses import replace

import pytest

import llm_router as package

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_INVALID_CONFIGURATION_ERRORS[revision==2]")
def test_install_config_policy_max_attempts_boundary() -> None:
    current = package.get_config()

    invalid_policy = replace(current.defaults.policy, max_attempts=0)
    invalid_defaults = replace(current.defaults, policy=invalid_policy)
    invalid_config = replace(current, defaults=invalid_defaults)
    with pytest.raises(package.ConfigurationError, match=r"policy max attempts"):
        package.install_config(invalid_config)
    assert package.get_config() is current

    valid_policy = replace(current.defaults.policy, max_attempts=1)
    valid_defaults = replace(current.defaults, policy=valid_policy)
    valid_config = replace(current, defaults=valid_defaults)
    installed = package.install_config(valid_config)
    assert installed is valid_config
    assert package.get_config() is valid_config

    package.install_config(current)

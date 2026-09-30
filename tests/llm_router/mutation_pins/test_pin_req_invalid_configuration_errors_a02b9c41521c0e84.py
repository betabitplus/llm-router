# mutation-pin: REQ_INVALID_CONFIGURATION_ERRORS a02b9c41521c0e84
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

from dataclasses import replace

import pytest

import llm_router as package

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_INVALID_CONFIGURATION_ERRORS[revision==2]")
def test_retry_max_attempts_boundary_one_valid_zero_rejected() -> None:
    original = package.get_config()

    def with_attempts(count: int):
        retry = replace(original.defaults.retry_policy, max_attempts=count)
        return replace(
            original, defaults=replace(original.defaults, retry_policy=retry)
        )

    installed = package.install_config(with_attempts(1))
    assert installed.retry_policy.max_attempts == 1

    with pytest.raises(
        package.ConfigurationError, match=r"^retry max attempts must be"
    ):
        package.install_config(with_attempts(0))

    assert package.get_config().retry_policy.max_attempts == 1
    package.install_config(original)

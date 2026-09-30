# mutation-pin: REQ_INVALID_CONFIGURATION_ERRORS 1e7fe255a9f2e635
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

from dataclasses import replace

import pytest

from llm_router import ConfigurationError, get_config, install_config

pytestmark = pytest.mark.verification_kind("unit")


def _with_min_routes(count: int):
    config = get_config()
    policy = replace(config.defaults.policy, min_routes_for_fallback_shuffle=count)
    return replace(config, defaults=replace(config.defaults, policy=policy))


@pytest.mark.verifies("REQ_INVALID_CONFIGURATION_ERRORS[revision==2]")
def test_min_routes_for_fallback_shuffle_boundary() -> None:
    original = get_config()
    valid = _with_min_routes(1)
    assert install_config(valid) is valid
    assert get_config() is valid
    install_config(original)

    invalid = _with_min_routes(0)
    with pytest.raises(
        ConfigurationError,
        match=r"^minimum routes for fallback shuffle must be at least 1\.$",
    ):
        install_config(invalid)
    assert get_config() is original

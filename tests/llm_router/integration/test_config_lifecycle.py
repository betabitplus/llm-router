"""Public config lifecycle integration tests."""

from __future__ import annotations

import pytest

from llm_router import LLMRouterConfig, get_config, install_config


def test_install_config_rejects_wrong_type() -> None:
    """The config lifecycle rejects unsupported config objects."""
    with pytest.raises(TypeError, match=r"install_config\(\) expects"):
        install_config(object())


def test_install_config_round_trips_real_snapshot() -> None:
    """The active immutable product config round-trips through installation."""
    config = get_config()

    assert isinstance(config, LLMRouterConfig)
    assert install_config(config) is config
    assert get_config() is config

"""Public config snapshot property tests."""

from __future__ import annotations

from hypothesis import given, strategies as st

from llm_router import LLMRouterConfig, get_config, install_config


@given(st.none())
def test_installed_config_snapshot_round_trips(value: None) -> None:
    """Generated no-op input does not change product config identity."""
    _ = value
    config = get_config()

    assert isinstance(config, LLMRouterConfig)
    assert install_config(config) is config
    assert get_config() is config

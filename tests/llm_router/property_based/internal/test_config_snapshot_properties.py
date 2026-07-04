from __future__ import annotations

from dataclasses import replace

from hypothesis import given, strategies as st

from llm_router import Provider, ProviderLimits
from llm_router._internal.config import build_default_config, get_config, install_config

_LIMITS = st.builds(
    ProviderLimits,
    rps=st.floats(min_value=0.1, max_value=100.0, allow_nan=False),
    rpm=st.floats(min_value=1.0, max_value=6000.0, allow_nan=False),
    cooldown_seconds=st.floats(min_value=0.0, max_value=120.0, allow_nan=False),
    cooldown_after_failures=st.integers(min_value=0, max_value=10),
)


@given(
    default_max_tool_rounds=st.integers(min_value=1, max_value=12),
    structured_output_max_attempts=st.integers(min_value=1, max_value=8),
    limits=_LIMITS,
)
def test_replaced_defaults_remain_installable_snapshots(
    *,
    default_max_tool_rounds: int,
    structured_output_max_attempts: int,
    limits: ProviderLimits,
) -> None:
    original = get_config()
    updated_defaults = replace(
        original.defaults,
        default_max_tool_rounds=default_max_tool_rounds,
        structured_output_max_attempts=structured_output_max_attempts,
        provider_limits=limits,
    )
    updated = replace(original, defaults=updated_defaults)

    try:
        install_config(updated)

        assert get_config().default_max_tool_rounds == default_max_tool_rounds
        assert (
            get_config().structured_output_max_attempts
            == structured_output_max_attempts
        )
        assert get_config().provider_limits == limits
    finally:
        install_config(original)


def test_catalog_replacement_copies_mutable_mappings() -> None:
    config = build_default_config()
    provider_base_urls = dict(config.provider_base_urls)
    provider_base_urls[Provider.AISTUDIO] = "http://aistudio.example.test/v1"

    updated_catalog = replace(config.catalog, provider_base_urls=provider_base_urls)
    provider_base_urls[Provider.AISTUDIO] = "http://mutated.example.test/v1"

    assert updated_catalog.provider_base_urls[Provider.AISTUDIO] == (
        "http://aistudio.example.test/v1"
    )

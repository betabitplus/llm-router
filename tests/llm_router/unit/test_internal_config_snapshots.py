from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import pytest

from llm_router import Provider
from llm_router._internal.config import build_default_config, get_config, install_config


def test_default_config_assembles_expected_snapshot_shape() -> None:
    config = build_default_config()

    assert config.default_provider is Provider.AISTUDIO
    assert config.default_key_id == 1
    assert Provider.AISTUDIO in config.catalog.providers
    assert Provider.AISTUDIO in config.provider_base_urls
    assert config.retry_policy.max_attempts == 5
    assert config.default_max_tool_rounds == 4
    assert config.structured_output_max_attempts == 3


def test_config_dataclasses_are_frozen() -> None:
    config = build_default_config()

    with pytest.raises(FrozenInstanceError):
        config.default_key_id = 2  # type: ignore[misc]


def test_config_mappings_do_not_alias_mutable_inputs() -> None:
    config = build_default_config()
    provider_base_urls = dict(config.provider_base_urls)
    updated_catalog = replace(config.catalog, provider_base_urls=provider_base_urls)

    provider_base_urls[Provider.AISTUDIO] = "http://mutated.example.test"

    assert updated_catalog.provider_base_urls[Provider.AISTUDIO] != (
        "http://mutated.example.test"
    )


def test_install_config_replaces_active_snapshot_atomically() -> None:
    original = get_config()
    updated_defaults = replace(original.defaults, default_max_tool_rounds=7)
    updated = replace(original, defaults=updated_defaults)

    try:
        installed = install_config(updated)

        assert installed is updated
        assert get_config() is updated
        assert get_config().default_max_tool_rounds == 7
    finally:
        install_config(original)

from __future__ import annotations

from llm_router import Provider
from llm_router._api.config import get_config, install_config
from llm_router._internal.providers.registry import (
    clear_adapter_caches,
    get_adapter,
    register_adapter_cache,
)


def test_adapter_cache_is_keyed_by_config_and_clearable() -> None:
    config = get_config()
    clear_adapter_caches()

    first = get_adapter(provider=Provider.OPENROUTER, config=config)
    second = get_adapter(provider=Provider.OPENROUTER, config=config)
    clear_adapter_caches()
    third = get_adapter(provider=Provider.OPENROUTER, config=config)

    assert first is second
    assert third is not first


def test_install_config_clears_registered_adapter_caches() -> None:
    config = get_config()
    cache: dict[str, object] = {"stale": object()}
    register_adapter_cache(cache)

    installed = install_config(config)

    assert installed is config
    assert cache == {}

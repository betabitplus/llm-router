from __future__ import annotations

from llm_router._api.config import get_config, install_config
from llm_router._internal.providers.registry import register_adapter_cache


def test_install_config_invalidates_registered_adapter_caches() -> None:
    config = get_config()
    cache: dict[str, object] = {"stale": object()}
    register_adapter_cache(cache)

    install_config(config)

    assert cache == {}

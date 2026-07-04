"""Provider adapter registry and cache ownership.

Why:
    Centralizes provider adapter cache lifecycle so config installs can clear
    stale clients through one private root export.
"""

from __future__ import annotations

from collections.abc import Callable, MutableMapping
from threading import RLock
from typing import Any

from llm_router._api.types import Provider
from llm_router._internal.config import LLMRouterConfig
from llm_router._internal.providers.base import ProviderAdapter
from llm_router._support.logging import get_logger

logger = get_logger(__name__)

AdapterFactory = Callable[[LLMRouterConfig, Provider], ProviderAdapter]

_adapter_caches: list[MutableMapping[Any, Any]] = []
_adapter_factories: dict[Provider, AdapterFactory] = {}
_adapter_instances: dict[tuple[int, Provider], ProviderAdapter] = {}
_adapter_caches.append(_adapter_instances)
_adapter_lock = RLock()


def register_adapter_factory(provider: Provider, factory: AdapterFactory) -> None:
    """Register an adapter factory for a provider."""
    with _adapter_lock:
        _adapter_factories[provider] = factory


def register_adapter_cache(cache: MutableMapping[Any, Any]) -> None:
    """Register an adapter-owned cache for global config-install clearing."""
    with _adapter_lock:
        if cache not in _adapter_caches:
            _adapter_caches.append(cache)


def get_adapter(
    *,
    provider: Provider,
    config: LLMRouterConfig,
) -> ProviderAdapter:
    """Return a cached adapter for one config snapshot and provider."""
    cache_key = (id(config), provider)
    with _adapter_lock:
        if cache_key in _adapter_instances:
            return _adapter_instances[cache_key]
        try:
            factory = _adapter_factories[provider]
        except KeyError as exc:
            msg = f"No provider adapter registered for '{provider.value}'."
            raise KeyError(msg) from exc
        _adapter_instances[cache_key] = factory(config, provider)
        return _adapter_instances[cache_key]


def clear_adapter_caches() -> None:
    """Clear all registered provider adapter caches."""
    with _adapter_lock:
        for cache in tuple(_adapter_caches):
            cache.clear()
    logger.info(
        "Provider adapter caches cleared",
        event_type="llm_router.config.adapter_caches.cleared",
    )


from llm_router._internal.providers.openai_compatible import (  # noqa: E402
    OPENAI_COMPATIBLE_PROVIDERS,
    adapter_from_config,
)

for _provider in OPENAI_COMPATIBLE_PROVIDERS:
    register_adapter_factory(_provider, adapter_from_config)


from llm_router._internal.providers.aistudio import (  # noqa: E402
    adapter_from_config as aistudio_adapter_from_config,
)
from llm_router._internal.providers.gemini_webapi import (  # noqa: E402
    adapter_from_config as gemini_webapi_adapter_from_config,
)
from llm_router._internal.providers.google_genai import (  # noqa: E402
    adapter_from_config as google_adapter_from_config,
)
from llm_router._internal.providers.qwenchat import (  # noqa: E402
    adapter_from_config as qwenchat_adapter_from_config,
)

register_adapter_factory(Provider.AISTUDIO, aistudio_adapter_from_config)
register_adapter_factory(Provider.GEMINI_WEBAPI, gemini_webapi_adapter_from_config)
register_adapter_factory(Provider.GOOGLE, google_adapter_from_config)
register_adapter_factory(Provider.QWENCHAT, qwenchat_adapter_from_config)

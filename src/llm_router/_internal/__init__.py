"""Private runtime package root for `llm_router`.

Why:
    Provides the narrow private root imported by public `_api` facade modules.

What belongs here:
    Only private entrypoints consumed directly by `_api.config`, `_api.router`,
    and `_api.session`.

What does not belong here:
    Provider adapters, runtime helper DTOs, capability helpers, or other deep
    implementation details.
"""

from llm_router._internal.config import (
    BehaviorDefaults,
    LLMRouterConfig,
    ProviderCatalog,
    ProviderSpec,
    RetryPolicy,
    RouterPolicyDefaults,
    get_config,
    install_config,
)
from llm_router._internal.providers.registry import clear_adapter_caches
from llm_router._internal.runtime import RouterRuntime
from llm_router._internal.session import SessionStore

__all__ = [
    "BehaviorDefaults",
    "LLMRouterConfig",
    "ProviderCatalog",
    "ProviderSpec",
    "RetryPolicy",
    "RouterPolicyDefaults",
    "RouterRuntime",
    "SessionStore",
    "clear_adapter_caches",
    "get_config",
    "install_config",
]

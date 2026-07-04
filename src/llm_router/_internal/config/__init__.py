"""Runtime configuration package.

Why:
    Owns validated immutable configuration snapshots for private router
    instances.

What belongs here:
    Config dataclasses, default assembly, validation, and process-wide snapshot
    state.

What does not belong here:
    Public facade helpers, provider client caches, or request execution logic.
"""

from llm_router._internal.config.assembly import build_default_config
from llm_router._internal.config.models import (
    BehaviorDefaults,
    LLMRouterConfig,
    ProviderCatalog,
    ProviderSpec,
    RetryPolicy,
    RouterPolicyDefaults,
)
from llm_router._internal.config.state import get_config, install_config
from llm_router._internal.config.validation import validate_config

__all__ = [
    "BehaviorDefaults",
    "LLMRouterConfig",
    "ProviderCatalog",
    "ProviderSpec",
    "RetryPolicy",
    "RouterPolicyDefaults",
    "build_default_config",
    "get_config",
    "install_config",
    "validate_config",
]

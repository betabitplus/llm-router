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

from llm_router._internal.config.assembly import (
    build_default_config as build_default_config,
)
from llm_router._internal.config.models import (
    BehaviorDefaults as BehaviorDefaults,
    LLMRouterConfig as LLMRouterConfig,
    ProviderCatalog as ProviderCatalog,
    ProviderSpec as ProviderSpec,
    RetryPolicy as RetryPolicy,
    RouterPolicyDefaults as RouterPolicyDefaults,
)
from llm_router._internal.config.state import (
    get_config as get_config,
    install_config as install_config,
)
from llm_router._internal.config.validation import validate_config as validate_config

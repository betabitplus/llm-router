"""Private implementation root for `llm_router`.

Public facade modules import authoritative product declarations and private
entrypoints only through this narrow package boundary.
"""

from __future__ import annotations

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
from llm_router._internal.contracts.errors import (
    LLMRouterError,
    ProviderError,
    ToolExecutionError,
    ConfigurationError,
    ModelNotFoundError,
    ProviderNotFoundError,
    ApiKeyNotFoundError,
)
from llm_router._internal.contracts.models import (
    FileSchema,
    ImageSchema,
    VideoSchema,
    VideoUrlSchema,
    MessageContent,
    ChatRole,
    ChatPart,
    ChatMessage,
    ProviderLimits,
    RouterConfig,
    RouterPolicy,
    RouterProfile,
    UsageStats,
    ToolCall,
    ToolStep,
    RoutingAttempt,
    LLMRouterResponse,
)
from llm_router._internal.contracts.types import (
    Provider,
    Model,
    KeyId,
)
from llm_router._internal.config.defaults import (
    DEFAULT_PROVIDER,
    DEFAULT_MODEL,
    DEFAULT_KEY_ID,
    DEFAULT_RETRY_MIN_WAIT_SECONDS,
    DEFAULT_RETRY_MAX_WAIT_SECONDS,
    DEFAULT_RETRY_MAX_ATTEMPTS,
    DEFAULT_POLICY_MAX_ATTEMPTS,
    DEFAULT_POLICY_ATTEMPT_TIMEOUT_SECONDS,
    DEFAULT_POLICY_WAIT_FOR_COOLDOWN_IF_ALL_BLOCKED,
    DEFAULT_POLICY_ROUND_ROBIN_START,
    DEFAULT_POLICY_SHUFFLE_FALLBACKS,
    DEFAULT_POLICY_MIN_ROUTES_FOR_FALLBACK_SHUFFLE,
    DEFAULT_MAX_TOOL_ROUNDS,
    DEFAULT_STRUCTURED_OUTPUT_MAX_ATTEMPTS,
    DEFAULT_PROVIDER_LIMITS,
    DEFAULT_LIMITS_BY_PROVIDER,
    DEFAULT_PROVIDER_BASE_URLS,
    DEFAULT_MODEL_REGISTRY,
)
from llm_router._internal.providers.registry import (
    clear_adapter_caches,
)
from llm_router._internal.runtime import (
    RouterRuntime,
)
from llm_router._internal.session import (
    SessionStore,
)

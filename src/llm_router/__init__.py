"""Supported public package entrypoint for `llm_router`.

Why:
    Exposes the stable public surface from one import boundary.

What belongs here:
    Re-exports of the router facade, public DTOs, config helpers, sessions,
    public exceptions, presets, and package version.

What does not belong here:
    Raw defaults, private runtime helpers, adapters, stores, or other
    implementation details.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as _pkg_version

from llm_router._api.config import (
    BehaviorDefaults,
    LLMRouterConfig,
    ProviderCatalog,
    ProviderSpec,
    RetryPolicy,
    RouterPolicyDefaults,
    get_config,
    install_config,
)
from llm_router._api.errors import (
    ApiKeyNotFoundError,
    ConfigurationError,
    LLMRouterError,
    ModelNotFoundError,
    ProviderError,
    ProviderNotFoundError,
    ToolExecutionError,
)
from llm_router._api.presets import Config, Policy, Profile
from llm_router._api.router import LLMRouter
from llm_router._api.session import Session
from llm_router._api.types import (
    ChatMessage,
    ChatPart,
    ChatRole,
    FileSchema,
    ImageSchema,
    KeyId,
    LLMRouterResponse,
    MessageContent,
    Model,
    Provider,
    ProviderLimits,
    RouterConfig,
    RouterPolicy,
    RouterProfile,
    RoutingAttempt,
    ToolCall,
    ToolStep,
    UsageStats,
    VideoSchema,
    VideoUrlSchema,
)

try:
    __version__ = _pkg_version("llm-router")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "unknown"

__all__ = [
    "ApiKeyNotFoundError",
    "BehaviorDefaults",
    "ChatMessage",
    "ChatPart",
    "ChatRole",
    "Config",
    "ConfigurationError",
    "FileSchema",
    "ImageSchema",
    "KeyId",
    "LLMRouter",
    "LLMRouterConfig",
    "LLMRouterError",
    "LLMRouterResponse",
    "MessageContent",
    "Model",
    "ModelNotFoundError",
    "Policy",
    "Profile",
    "Provider",
    "ProviderCatalog",
    "ProviderError",
    "ProviderLimits",
    "ProviderNotFoundError",
    "ProviderSpec",
    "RetryPolicy",
    "RouterConfig",
    "RouterPolicy",
    "RouterPolicyDefaults",
    "RouterProfile",
    "RoutingAttempt",
    "Session",
    "ToolCall",
    "ToolExecutionError",
    "ToolStep",
    "UsageStats",
    "VideoSchema",
    "VideoUrlSchema",
    "__version__",
    "get_config",
    "install_config",
]

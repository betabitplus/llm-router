"""Public built-in default declarations for `llm_router`.

Why:
    Keeps shared built-in defaults in one declarative place instead of
    scattering them across runtime code.

How:
    Treat these values as source declarations, not mutable runtime state.
    Config assembly is responsible for validating, copying, and freezing them
    before request execution begins.

Notes:
    This module answers the question "what does the library do by default
    before the user installs a custom config?".

    It covers:
    - the default provider/model route
    - retry and routing policy defaults
    - built-in tool and structured-output limits
    - default provider limiter values and base URLs
    - the public-model-to-provider-model registry
"""

from __future__ import annotations

from llm_router._internal.contracts.models import ProviderLimits
from llm_router._internal.contracts.types import Model, Provider

# ================================================================================
# Default Route Selection
# ================================================================================


# The library comes with one built-in default route so a caller can construct
# `LLMRouter(...)` without first installing custom config.
DEFAULT_PROVIDER: Provider = Provider.AISTUDIO
DEFAULT_MODEL: Model = Model.GEMINI_FLASH
DEFAULT_KEY_ID: int = 1


# ================================================================================
# Retry Defaults
# ================================================================================


# These defaults govern provider-level retry behavior inside the library.
# They are separate from routing fallback and separate from any third-party SDK
# retry behavior, which the project generally disables where possible.
DEFAULT_RETRY_MIN_WAIT_SECONDS: float = 2.0
DEFAULT_RETRY_MAX_WAIT_SECONDS: float = 60.0
DEFAULT_RETRY_MAX_ATTEMPTS: int = 5


# ================================================================================
# Routing Policy Defaults
# ================================================================================


# `None` means "do not cap attempts at the policy layer; allow the route set".
DEFAULT_POLICY_MAX_ATTEMPTS: int | None = None
# `None` means "no attempt timeout". The current built-in default is a
# generous timeout rather than a fully disabled timeout.
DEFAULT_POLICY_ATTEMPT_TIMEOUT_SECONDS: float | None = 600.0
DEFAULT_POLICY_WAIT_FOR_COOLDOWN_IF_ALL_BLOCKED: bool = True
DEFAULT_POLICY_ROUND_ROBIN_START: bool = True
DEFAULT_POLICY_SHUFFLE_FALLBACKS: bool = True
DEFAULT_POLICY_MIN_ROUTES_FOR_FALLBACK_SHUFFLE: int = 3


# ================================================================================
# Tooling / Structured Output Defaults
# ================================================================================


# Tool-calling rounds are bounded so the router cannot loop forever on repeated
# tool requests. Structured-output repair loops use a separate cap.
DEFAULT_MAX_TOOL_ROUNDS: int = 4
DEFAULT_STRUCTURED_OUTPUT_MAX_ATTEMPTS: int = 3


# ================================================================================
# Provider Catalog Defaults
# ================================================================================


# Provider limits are applied per `(provider, key_id)` limiter bucket.
DEFAULT_PROVIDER_LIMITS: ProviderLimits = ProviderLimits(
    rps=1.0,
    rpm=10.0,
    cooldown_seconds=600.0,
    cooldown_after_failures=3,
)

# Empty by default means "use the shared provider limits for every provider
# unless config installs a per-provider override".
DEFAULT_LIMITS_BY_PROVIDER: dict[Provider, ProviderLimits] = {}

# Only providers that require custom base URLs appear here. Providers whose SDKs
# do not need a base URL are modeled elsewhere in installed config.
DEFAULT_PROVIDER_BASE_URLS: dict[Provider, str] = {
    Provider.AISTUDIO: "http://localhost:7860/v1",
    Provider.QWENCHAT: "http://localhost:3264/api",
    Provider.OPENROUTER: "https://openrouter.ai/api/v1",
    Provider.MISTRAL: "https://api.mistral.ai/v1",
    Provider.NVIDIA: "https://integrate.api.nvidia.com/v1",
    Provider.GROQ: "https://api.groq.com/openai/v1",
    Provider.ALIBABA: "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
}


# ================================================================================
# Model Registry Defaults
# ================================================================================


# This registry maps the public `Model` vocabulary to concrete provider-native
# model names. A single public model may map to different concrete names across
# providers, or to multiple providers at once.
DEFAULT_MODEL_REGISTRY: dict[Model, dict[Provider, str]] = {
    Model.GEMINI_FLASH_LITE: {
        Provider.GOOGLE: "gemini-2.5-flash-lite",
        Provider.AISTUDIO: "gemini-2.5-flash-lite",
        Provider.GEMINI_WEBAPI: "gemini-3.0-flash",
    },
    Model.GEMINI_FLASH: {
        Provider.GOOGLE: "gemini-2.5-flash",
        Provider.AISTUDIO: "gemini-2.5-flash",
        Provider.GEMINI_WEBAPI: "gemini-3.0-flash",
    },
    Model.GEMINI_FLASH_2_0: {
        Provider.GOOGLE: "gemini-2.0-flash",
        Provider.AISTUDIO: "gemini-2.0-flash",
        Provider.GEMINI_WEBAPI: "gemini-3.0-flash",
    },
    Model.GEMINI_PRO: {
        Provider.GOOGLE: "gemini-2.5-pro",
        Provider.AISTUDIO: "gemini-2.5-pro",
        Provider.GEMINI_WEBAPI: "gemini-3.0-pro",
    },
    Model.GEMINI_3_FLASH: {
        Provider.GOOGLE: "gemini-3-flash-preview",
        Provider.AISTUDIO: "gemini-3-flash-preview",
        Provider.GEMINI_WEBAPI: "gemini-3.0-flash",
    },
    Model.DEEPSEEK_V3: {
        Provider.OPENROUTER: "deepseek/deepseek-chat-v3-0324:free",
    },
    Model.QWEN_VL_32B: {
        Provider.OPENROUTER: "qwen/qwen2.5-vl-32b-instruct:free",
        Provider.QWENCHAT: "qwen2.5-vl-32b-instruct",
    },
    Model.MISTRAL_LARGE: {Provider.MISTRAL: "mistral-large-latest"},
    Model.PIXTRAL_LARGE: {Provider.MISTRAL: "pixtral-large-latest"},
    Model.LLAMA_MAVERICK: {
        Provider.NVIDIA: "meta/llama-4-maverick-17b-128e-instruct",
    },
    Model.LLAMA_SCOUT: {
        Provider.GROQ: "meta-llama/llama-4-scout-17b-16e-instruct",
    },
    Model.QWEN_VL_3B: {Provider.ALIBABA: "qwen2.5-vl-3b-instruct"},
    Model.QWEN_MAX_LATEST: {Provider.QWENCHAT: "qwen-max-latest"},
    Model.QWEN3_235B_A22B: {
        Provider.QWENCHAT: "qwen3-235b-a22b",
        Provider.NVIDIA: "qwen/qwen3-235b-a22b",
    },
    Model.QWEN3_5_397B_A17B: {
        Provider.QWENCHAT: "qwen3.5-397b-a17b",
        Provider.NVIDIA: "qwen/qwen3.5-397b-a17b",
    },
    Model.QWEN3_VL_PLUS: {Provider.QWENCHAT: "qwen3-vl-plus"},
}


# ================================================================================
# Internal Classification
# ================================================================================


# Private support metadata used by config assembly to know which providers must
# have a configured base URL.
_PROVIDERS_REQUIRING_BASE_URL: frozenset[Provider] = frozenset(
    {
        Provider.AISTUDIO,
        Provider.QWENCHAT,
        Provider.OPENROUTER,
        Provider.MISTRAL,
        Provider.NVIDIA,
        Provider.GROQ,
        Provider.ALIBABA,
    }
)

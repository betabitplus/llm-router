"""Compatibility facade for built-in `llm_router` defaults.

Defaults are implementation inputs owned by private config assembly. Existing
imports remain valid through this facade."""

from __future__ import annotations

# pyright: reportUnusedImport=false
from llm_router._internal import (  # noqa: F401
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

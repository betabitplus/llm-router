"""Public exception facade for `llm_router`.

The exported classes keep their public identity while private code imports the
authoritative declarations without depending on facade modules."""

from __future__ import annotations

# pyright: reportUnusedImport=false
from llm_router._internal import (  # noqa: F401
    LLMRouterError,
    ProviderError,
    ToolExecutionError,
    ConfigurationError,
    ModelNotFoundError,
    ProviderNotFoundError,
    ApiKeyNotFoundError,
)

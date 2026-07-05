"""Public exceptions for `llm_router`.

Why:
    Keeps the caller-facing exception taxonomy stable and separate from
    private normalization and transport details.

How:
    Runtime internals may translate provider SDK failures, routing failures,
    and config failures into the public exceptions defined here before they
    cross the package boundary.

Notes:
    Important public boundary rules:
    - direct caller input validation may still use built-in `TypeError` or
      `ValueError`
    - operational failures that matter across the package boundary should use
      typed public exceptions from this module
    - messages should help callers understand what failed without exposing
      secrets, full payloads, or provider-specific internals by default
"""

from py_lib_runtime import (
    preview_exception_message,
    preview_mapping,
    preview_text,
)

from llm_router._api.types import Model, Provider

# ================================================================================
# Base Error Types
# ================================================================================


class LLMRouterError(Exception):
    """Base exception for the public `llm_router` failure taxonomy."""


# ================================================================================
# Public Execution Errors
# ================================================================================


class ProviderError(LLMRouterError):
    """Provider-side failure exposed through the public boundary.

    This is the main execution error for failures that happen after the router
    has chosen a route and attempted provider work. It is raised after
    provider-specific retries and normalization have already happened.
    """

    def __init__(
        self,
        cause: Exception,
        provider: Provider | str,
        model: Model | str,
        *,
        message: str | None = None,
    ) -> None:
        """Create a caller-facing provider failure.

        Args:
            cause:
                The original underlying exception.
            provider:
                Public provider identifier for the failing route.
            model:
                Public model identifier or concrete model string associated
                with the failure.
            message:
                Optional normalized message override. When omitted, a safe
                preview is derived from `cause`.
        """
        self.cause = cause
        self.provider = provider
        self.model = model
        final_message = (
            "Provider "
            f"'{provider}' failed for model '{model}'. "
            f"Original error: {preview_text(message)}"
            if message is not None
            else "Provider "
            f"'{provider}' failed for model '{model}'. "
            f"Original error: {preview_exception_message(cause)}"
        )
        super().__init__(final_message)


class ToolExecutionError(LLMRouterError):
    """Local tool execution failed during a tool-calling request.

    This error is about the Python tool implementation the application
    provided, not about the upstream model choosing tools.
    """

    def __init__(
        self,
        *,
        tool_name: str,
        args: dict[str, object],
        cause: Exception,
    ) -> None:
        """Create a caller-facing local tool failure."""
        self.tool_name = tool_name
        self.args = args
        self.cause = cause
        args_preview = preview_mapping(args)
        super().__init__(
            f"Tool '{tool_name}' failed with args {args_preview}. "
            f"Original error: {preview_exception_message(cause)}"
        )


# ================================================================================
# Public Configuration Errors
# ================================================================================


class ConfigurationError(LLMRouterError):
    """Invalid, inconsistent, or missing router configuration."""


class ModelNotFoundError(ConfigurationError):
    """Configured provider has no concrete mapping for the requested model."""

    def __init__(self, model: Model, provider: Provider) -> None:
        """Create a missing-model mapping error."""
        self.model = model
        self.provider = provider
        super().__init__(
            f"Model '{model.value}' not configured for provider '{provider.value}'."
        )


class ProviderNotFoundError(ConfigurationError):
    """Requested provider is not declared in the installed config."""

    def __init__(self, provider: Provider) -> None:
        """Create a missing-provider error."""
        self.provider = provider
        super().__init__(f"Provider '{provider.value}' not found in config.")


class ApiKeyNotFoundError(ConfigurationError):
    """Required provider API key could not be resolved from the environment."""

    def __init__(self, key_name: str, provider: str, key_id: int) -> None:
        """Create a missing-key error with the expected key name."""
        self.key_name = key_name
        self.provider = provider
        self.key_id = key_id
        super().__init__(
            f"API key '{key_name}' not found for provider '{provider}' (ID: {key_id})."
        )

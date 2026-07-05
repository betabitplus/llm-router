"""Provider adapter ports and DTOs.

Why:
    Defines the provider-neutral contract used by runtime orchestration before
    concrete adapters translate requests into SDK-specific payloads.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Protocol

from llm_router._api.types import Model, Provider, ToolCall, UsageStats
from llm_router._internal.capabilities.content import NormalizedMessage
from llm_router._internal.capabilities.schema import SchemaSpec
from llm_router._internal.capabilities.tools import ToolChoice, ToolRegistry


@dataclass(frozen=True, slots=True)
class ProviderCredential:
    """Credential selected for one provider request."""

    key_id: int
    env_var: str
    value: str


@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    """Feature switches exposed by one adapter."""

    supports_images: bool = False
    supports_files: bool = False
    supports_video: bool = False
    supports_json_schema: bool = False
    supports_tools: bool = False


@dataclass(frozen=True, slots=True)
class ProviderRequest:
    """Provider-neutral request envelope."""

    request_id: str
    provider: Provider
    model: Model
    provider_model: str
    credential: ProviderCredential
    messages: Sequence[NormalizedMessage]
    temperature: float | None = None
    seed: int | None = None
    schema: SchemaSpec | None = None
    tool_registry: ToolRegistry | None = None
    tool_choice: ToolChoice | None = None
    kwargs: Mapping[str, Any] = field(default_factory=dict)
    route_index: int | None = None

    def __post_init__(self) -> None:
        """Copy mutable request fields after construction."""
        object.__setattr__(self, "messages", tuple(self.messages))
        object.__setattr__(self, "kwargs", MappingProxyType(dict(self.kwargs)))

    def log_context(self) -> dict[str, object]:
        """Return common safe fields for provider and capability logs."""
        context: dict[str, object] = {
            "request_id": self.request_id,
            "provider": self.provider.value,
            "model": self.model.value,
            "key_id": self.credential.key_id,
        }
        if self.route_index is not None:
            context["route_index"] = self.route_index
        return context


@dataclass(frozen=True, slots=True)
class ProviderResult:
    """Provider-neutral successful result envelope."""

    data: Mapping[str, Any]
    provider: Provider
    model: Model
    provider_model: str
    output_text: str
    usage: UsageStats | None = None
    tool_calls: tuple[ToolCall, ...] = ()

    def __post_init__(self) -> None:
        """Copy mutable provider result data after construction."""
        object.__setattr__(self, "data", MappingProxyType(dict(self.data)))
        object.__setattr__(self, "tool_calls", tuple(self.tool_calls))


@dataclass(frozen=True, slots=True)
class ProviderFailure(Exception):  # noqa: N818
    """Provider failure classified before public boundary translation."""

    provider: Provider
    model: Model
    message: str
    retryable: bool
    status_code: int | None = None
    retry_reason: str | None = None

    def __str__(self) -> str:
        """Return the safe failure message."""
        return self.message


class ProviderAdapter(Protocol):
    """Protocol implemented by concrete provider adapters."""

    capabilities: ProviderCapabilities

    def execute(self, request: ProviderRequest) -> ProviderResult:
        """Execute one synchronous provider request."""

    async def aexecute(self, request: ProviderRequest) -> ProviderResult:
        """Execute one asynchronous provider request."""

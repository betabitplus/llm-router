"""Public schemas and DTOs for `llm_router`.

Why:
    Keeps the caller-facing request, response, media, session, routing, and
    trace contracts in one stable declaration layer.

How:
    This module is the best place to learn the public data model of the
    library. The private runtime may be complex, but nearly all caller-visible
    shapes flow through the types defined here.

Notes:
    Three important ideas shape this module:

    - request content is role-less at the public boundary; callers submit a
      string or `MessageContent`, while the runtime adapts that into provider-
      specific message formats
    - route intent is described with public profiles, configs, and policies,
      not with provider SDK objects
    - responses are normalized into one wrapper that always includes public
      output text, provider/model identity, usage when available, and routing
      trace information
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Any, Literal
from urllib.parse import urlparse

from PIL import Image
from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from llm_router._api.types import KeyId, Model, Provider

# =============================================================================
# Helpers
# =============================================================================


def _validate_is_file(path: str, *, error_template: str) -> str:
    """Return normalized file path if it exists and is a file."""
    p = Path(path)
    if not p.is_file():
        msg = error_template.format(path=path)
        raise ValueError(msg)
    return str(p)


def _as_explicit_kwargs(
    *items: tuple[str, Any],
    copied_mappings: Mapping[str, Mapping[Any, Any]] | None = None,
) -> dict[str, Any]:
    """Return kwargs containing only explicitly configured non-null values."""
    data = {key: value for key, value in items if value is not None}
    if copied_mappings is None:
        return data

    for key, value in copied_mappings.items():
        data[key] = dict(value)
    return data


# =============================================================================
# Input / upload schemas
# =============================================================================


class FileSchema(BaseModel):
    """Validated local file input for provider upload flows.

    Use this for non-image file inputs such as PDFs or other provider-supported
    local file types. Validation is intentionally lightweight at this layer:
    the path must exist and be a file, while provider-specific compatibility is
    enforced later by the adapter handling the request.
    """

    path: str
    mime_type: str | None = None

    @field_validator("path")
    @classmethod
    def validate_path(cls, path: str) -> str:
        """Validate that the file path exists and points to a file."""
        return _validate_is_file(
            path,
            error_template="File path does not exist: {path}",
        )


def _validate_image(image: Image.Image) -> Image.Image:
    """Validate image dimensions and mode for downstream processing."""
    if image.width <= 0 or image.height <= 0:
        msg = f"Image must have positive dimensions, got {image.width}x{image.height}."
        raise ValueError(msg)

    allowed_modes = {"RGB", "RGBA", "L", "LA", "P", "PA"}
    if image.mode not in allowed_modes:
        msg = (
            f"Image mode {image.mode!r} is not supported. "
            f"Allowed: {sorted(allowed_modes)}."
        )
        raise ValueError(msg)

    min_dim = 10
    max_dim = 16384
    if image.width < min_dim or image.height < min_dim:
        msg = (
            f"Image dimensions {image.width}x{image.height} are too small "
            f"(min {min_dim}x{min_dim})."
        )
        raise ValueError(msg)
    if image.width > max_dim or image.height > max_dim:
        msg = (
            f"Image dimensions {image.width}x{image.height} are too large "
            f"(max {max_dim}x{max_dim})."
        )
        raise ValueError(msg)

    return image


# `ImageSchema` is a validated Pillow image object. The alias stays lightweight
# on purpose so callers can use ordinary in-memory images instead of wrapper
# DTOs for the most common multimodal case.
ImageSchema = Annotated[
    Image.Image,
    AfterValidator(_validate_image),
]


class VideoSchema(BaseModel):
    """Validated local video input.

    This describes a local video file plus optional public sampling hints used
    by providers that support video processing.
    """

    path: str
    fps: int = 1
    start_offset: int | None = None
    end_offset: int | None = None

    @field_validator("path")
    @classmethod
    def validate_path(cls, path: str) -> str:
        """Validate that the path exists and points to a file."""
        return _validate_is_file(
            path,
            error_template="Video file not found at path: {path}",
        )


class VideoUrlSchema(BaseModel):
    """Validated remote video URL input with optional sampling hints."""

    url: str
    fps: int = 1
    start_offset: int | None = None
    end_offset: int | None = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, url: str) -> str:
        """Validate that the string is a well-formed absolute URL."""
        try:
            parsed = urlparse(url)
        except ValueError as exc:
            msg = f"Invalid video URL: {url}"
            raise ValueError(msg) from exc
        if not parsed.scheme or not parsed.netloc:
            msg = f"Invalid video URL: {url}"
            raise ValueError(msg)
        return url


# =============================================================================
# Common type aliases
# =============================================================================


# Type alias for unified role-less message input.
#
# This is one of the core public design choices in the project: callers submit
# content without manually building provider-flavored chat payloads.
MessageContent = Sequence[str | ImageSchema | VideoSchema | VideoUrlSchema | FileSchema]

ChatRole = Literal["user", "assistant"]
ChatPart = str | ImageSchema | VideoSchema | VideoUrlSchema | FileSchema


@dataclass(slots=True)
class ChatMessage:
    """Single message in a public chat transcript snapshot.

    `Session.history` is exposed as a sequence of these records. `meta` is
    intentionally open-ended so the library can persist assistant-side routing,
    provider, and usage details without forcing a second transcript type.
    """

    role: ChatRole
    parts: tuple[ChatPart, ...]
    meta: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Router configuration / DTOs
# =============================================================================


@dataclass(frozen=True, slots=True)
class ProviderLimits:
    """Per-provider limiter and cooldown defaults.

    These values apply to one `(provider, key_id)` bucket. They describe how
    frequently the router should issue requests for that bucket and when it
    should temporarily cool down after repeated failures.
    """

    rps: float
    rpm: float
    cooldown_seconds: float
    cooldown_after_failures: int

    def min_interval_seconds(self) -> float:
        """Return the conservative spacing interval implied by `rps` and `rpm`."""
        intervals: list[float] = []
        if self.rps > 0:
            intervals.append(1.0 / self.rps)
        if self.rpm > 0:
            intervals.append(60.0 / self.rpm)
        return max(intervals) if intervals else 0.0


@dataclass(frozen=True, slots=True)
class RouterConfig:
    """Reusable generation defaults for a router or one route.

    This is the public bundle for "how should a request be generated?" rather
    than "where should it be routed?".

    Use it when you want to package generation settings as data, pass them
    around, and later expand them into `LLMRouter(...)` or `RouterProfile(...)`
    kwargs with `as_kwargs()`.
    """

    temperature: float | None = None
    seed: int | None = None
    response_schema: type[BaseModel] | dict[str, Any] | None = None
    tools: Sequence[Callable[..., Any] | dict[str, Any]] | None = None
    tool_choice: str | dict[str, Any] | None = None
    max_tool_rounds: int | None = None
    kwargs: dict[str, Any] = field(default_factory=dict)

    def as_kwargs(self) -> dict[str, Any]:
        """Return explicit non-null fields as constructor kwargs.

        This keeps `None` values out of the expansion so they do not overwrite
        other layered defaults unintentionally.
        """
        copied_mappings: dict[str, Mapping[Any, Any]] = {}
        if self.kwargs:
            copied_mappings["kwargs"] = self.kwargs
        return _as_explicit_kwargs(
            ("temperature", self.temperature),
            ("seed", self.seed),
            ("response_schema", self.response_schema),
            ("tools", self.tools),
            ("tool_choice", self.tool_choice),
            ("max_tool_rounds", self.max_tool_rounds),
            copied_mappings=copied_mappings or None,
        )


@dataclass(frozen=True, slots=True)
class RouterPolicy:
    """Reusable routing and fallback policy defaults.

    This bundle controls route-order and resilience decisions such as maximum
    route attempts, per-attempt timeouts, cooldown waiting, fallback
    shuffling, and limiter defaults.
    """

    max_attempts: int | None = None
    attempt_timeout_seconds: float | None = None
    wait_for_cooldown_if_all_blocked: bool | None = None
    round_robin_start: bool | None = None
    shuffle_fallbacks: bool | None = None

    default_limits: ProviderLimits | None = None
    limits_by_provider: dict[Provider, ProviderLimits] | None = None

    def as_kwargs(self) -> dict[str, Any]:
        """Return explicit non-null policy fields as constructor kwargs."""
        copied_mappings: dict[str, Mapping[Any, Any]] = {}
        if self.limits_by_provider is not None:
            copied_mappings["limits_by_provider"] = self.limits_by_provider
        return _as_explicit_kwargs(
            ("max_attempts", self.max_attempts),
            ("attempt_timeout_seconds", self.attempt_timeout_seconds),
            (
                "wait_for_cooldown_if_all_blocked",
                self.wait_for_cooldown_if_all_blocked,
            ),
            ("round_robin_start", self.round_robin_start),
            ("shuffle_fallbacks", self.shuffle_fallbacks),
            ("default_limits", self.default_limits),
            copied_mappings=copied_mappings or None,
        )


@dataclass(frozen=True, slots=True)
class RouterProfile:
    """Single route definition with attachable defaults.

    A `RouterProfile` describes one route the runtime can attempt.

    It can carry:
    - route identity: public model, optional explicit provider, optional key
      selection
    - generation defaults: temperature, seed, tools, structured output, and
      extra provider kwargs
    - router-wide policy defaults: fallback/timeout/limiter settings

    Important nuance:
    if `provider` is omitted, the runtime may expand this one public profile
    into multiple concrete routes based on the installed model registry.

    Important policy nuance:
    policy fields attached to profiles are router-wide defaults. If multiple
    profiles provide conflicting values for those fields, runtime construction
    fails rather than silently picking one.
    """

    model: Model | str
    provider: Provider | str | None = None
    key_id: KeyId | None = None

    # Generation defaults
    temperature: float | None = None
    seed: int | None = None
    response_schema: type[BaseModel] | dict[str, Any] | None = None
    tools: Sequence[Callable[..., Any] | dict[str, Any]] | None = None
    tool_choice: str | dict[str, Any] | None = None
    max_tool_rounds: int | None = None
    kwargs: dict[str, Any] = field(default_factory=dict)

    # Policy defaults (router-wide; must not conflict across routes)
    max_attempts: int | None = None
    attempt_timeout_seconds: float | None = None
    wait_for_cooldown_if_all_blocked: bool | None = None
    round_robin_start: bool | None = None
    shuffle_fallbacks: bool | None = None
    default_limits: ProviderLimits | None = None
    limits_by_provider: dict[Provider, ProviderLimits] | None = None


# =============================================================================
# Responses / traces
# =============================================================================


class UsageStats(BaseModel):
    """Normalized token usage statistics.

    Some providers expose exact counts, some expose partial counts, and some
    expose none. The public shape stays stable either way.
    """

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


class ToolCall(BaseModel):
    """Normalized tool call request produced by the model."""

    id: str | None = None
    name: str
    args: dict[str, Any] = Field(default_factory=dict)
    raw_arguments: str | None = None


class ToolStep(BaseModel):
    """Executed tool call plus local result for reproducible traces."""

    tool_name: str
    args: dict[str, Any] = Field(default_factory=dict)
    result: Any = None
    call_id: str | None = None


class RoutingAttempt(BaseModel):
    """Single routing attempt in the public orchestration trace.

    Each entry records one concrete route attempt after route expansion and key
    selection have already happened. A successful response can still include
    failed attempts before the final success.
    """

    profile_name: str | None = None
    route_index: int
    provider: str
    model: str
    key_id: int

    wait_seconds: float = 0.0
    temperature: float | None = None
    seed: int | None = None
    max_tool_rounds: int

    error_type: str | None = None
    error_message: str | None = None


class LLMRouterResponse(BaseModel):
    """Standardized public response wrapper.

    This is the single normalized result shape returned by `query()` and
    `aquery()` no matter which provider family executed the request.

    Fields:
        data:
            Raw provider response object or parsed provider payload.
        usage:
            Normalized token usage when available.
        provider, model:
            Public route identity for the successful response.
        output_text:
            Flattened text output for the common case.
        tool_calls:
            Normalized tool calls produced by the model.
        tool_trace:
            Local tool execution trace captured by the library.
        routing_trace:
            Ordered route-attempt trace captured by the library.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    data: Any  # Raw response from provider
    usage: UsageStats | None = None
    provider: str
    model: str
    output_text: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tool_trace: list[ToolStep] = Field(default_factory=list)
    routing_trace: list[RoutingAttempt] = Field(default_factory=list)

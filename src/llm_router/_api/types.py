"""Public vocabulary and data contracts for `llm_router`.

This declaration module owns all caller-facing enums, aliases, request DTOs,
response DTOs, routing profiles, and trace shapes shared with private runtime
code.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
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


class _PathValidator:
    """Validate local paths used by public file and video DTOs."""

    @staticmethod
    def validate(path: str, *, error_template: str) -> str:
        """Return a normalized existing file path."""
        file_path = Path(path)
        if not file_path.is_file():
            msg = error_template.format(path=path)
            raise ValueError(msg)
        return str(file_path)


class _ExplicitKwargsBuilder:
    """Build defensive copies of explicitly configured DTO fields."""

    @staticmethod
    def build(
        *items: tuple[str, Any],
        copied_mappings: Mapping[str, Mapping[Any, Any]] | None = None,
    ) -> dict[str, Any]:
        """Return only explicitly configured non-null values."""
        data = {key: value for key, value in items if value is not None}
        if copied_mappings is not None:
            for key, value in copied_mappings.items():
                data[key] = dict(value)
        return data


class _ImageValidator:
    """Validate public in-memory image inputs."""

    @staticmethod
    def validate(image: Image.Image) -> Image.Image:
        """Return an image with supported dimensions and mode."""
        if image.width <= 0 or image.height <= 0:
            msg = (
                "Image must have positive dimensions, "
                f"got {image.width}x{image.height}."
            )
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


class Provider(StrEnum):
    """Supported public provider identifiers.

    These values are stable routing names used across config, profiles,
    routing traces, and public error messages.
    """

    GOOGLE = "google"
    AISTUDIO = "aistudio"
    GEMINI_WEBAPI = "gemini_webapi"
    QWENCHAT = "qwenchat"
    OPENROUTER = "openrouter"
    MISTRAL = "mistral"
    NVIDIA = "nvidia"
    GROQ = "groq"
    ALIBABA = "alibaba"


class Model(StrEnum):
    """Supported public model identifiers.

    A `Model` is a portable model intent, not necessarily the exact string sent
    to a provider API. The configured model registry maps each public model to
    one or more provider-specific concrete names.
    """

    # Gemini models
    GEMINI_FLASH_LITE = "gemini-2.5-flash-lite"
    GEMINI_FLASH = "gemini-2.5-flash"
    GEMINI_FLASH_2_0 = "gemini-2.0-flash"
    GEMINI_PRO = "gemini-2.5-pro"
    GEMINI_3_FLASH = "gemini-3-flash"

    # OpenRouter models
    DEEPSEEK_V3 = "deepseek-chat-v3"
    QWEN_VL_32B = "qwen2.5-vl-32b-instruct"

    # Mistral models
    MISTRAL_LARGE = "mistral-large-latest"

    # NVIDIA models
    LLAMA_MAVERICK = "llama-4-maverick"

    # Groq models
    LLAMA_SCOUT = "llama-4-scout"

    # Alibaba models
    QWEN_VL_3B = "qwen2.5-vl-3b-instruct"

    # QwenChat models (FreeQwenApi)
    QWEN_MAX_LATEST = "qwen-max-latest"
    QWEN3_235B_A22B = "qwen3-235b-a22b"
    QWEN3_5_397B_A17B = "qwen3.5-397b-a17b"
    QWEN3_VL_PLUS = "qwen3-vl-plus"


# Common small type aliases (stdlib-only).
# `KeyId` is used anywhere the public API needs to pick credentials for a
# provider route. Integers pin one concrete key slot, while `"auto"` asks the
# runtime to choose among discovered keys for that provider.
KeyId = int | Literal["auto"]


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
        return _PathValidator.validate(
            path,
            error_template="File path does not exist: {path}",
        )


# `ImageSchema` is a validated Pillow image object. The alias stays lightweight
# on purpose so callers can use ordinary in-memory images instead of wrapper
# DTOs for the most common multimodal case.
ImageSchema = Annotated[
    Image.Image,
    AfterValidator(_ImageValidator.validate),
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
        return _PathValidator.validate(
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
        return _ExplicitKwargsBuilder.build(
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
        return _ExplicitKwargsBuilder.build(
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

"""Public execution facade for `llm_router`.

Why:
    Provides the main caller-facing router entrypoint over the private routing
    runtime.

How:
    Keep the public constructor and call signatures here, perform only the
    small amount of caller-facing shaping that belongs at the facade boundary,
    and then forward into private orchestration.

Notes:
    `LLMRouter` is intentionally thin, but it still captures several important
    public semantics:

    - `spec` can be a single `Model`, a pinned `RouterProfile`, or a sequence
      of profiles representing one fallback route set
    - constructor arguments define reusable defaults for that router instance
    - `query()` / `aquery()` allow only explicit per-call generation overrides
    - omitted per-call values stay omitted, which is different from passing
      `None` intentionally
    - routing policy is configured at router construction time, not ad hoc on
      every call

Examples:
    router = LLMRouter(Model.GEMINI_FLASH)
    response = router.query("Reply only OK.")

    router = LLMRouter(
        [
            RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.GOOGLE),
            RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.AISTUDIO),
        ],
        max_attempts=2,
    )
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, Final

from pydantic import BaseModel

from llm_router._api.session import Session
from llm_router._api.types import (
    KeyId,
    LLMRouterResponse,
    MessageContent,
    Model,
    Provider,
    ProviderLimits,
    RouterProfile,
)
from llm_router._internal import RouterRuntime

# ================================================================================
# Call Override Sentinel
# ================================================================================


class _CallUnset:
    """Facade-local sentinel for an omitted per-call override.

    The public API needs to distinguish these cases cleanly:
    - caller omitted the field entirely
    - caller explicitly passed `None`

    That distinction matters because the runtime applies layered defaults from
    config, route, router, and per-call state.
    """


CALL_UNSET: Final = _CallUnset()


# ================================================================================
# Helpers
# ================================================================================


def _include_if_set(
    target: dict[str, object],
    *,
    key: str,
    value: object,
) -> None:
    """Copy only explicitly provided facade values into runtime kwargs."""
    if value is not CALL_UNSET:
        target[key] = value


def _build_call_kwargs(
    *,
    kwargs: dict[str, object],
    overrides: Sequence[tuple[str, object]],
) -> dict[str, object]:
    """Return runtime kwargs with only explicit per-call overrides included."""
    runtime_kwargs = dict(kwargs)
    for key, value in overrides:
        _include_if_set(runtime_kwargs, key=key, value=value)
    return runtime_kwargs


# ================================================================================
# Public API
# ================================================================================


class LLMRouter:
    """Stable public router facade over the private routing runtime.

    This is the main object application code works with. A router instance
    binds together:

    - what route or route set should be attempted
    - optional reusable generation defaults
    - optional reusable routing policy defaults
    - optional session continuity state

    `spec` supports three public entry shapes:

    - `Model`: the simplest form; provider selection can be expanded from the
      installed model registry
    - `RouterProfile`: one explicit route definition, optionally with pinned
      provider, key choice, and route defaults
    - `Sequence[RouterProfile]`: a fallback route set tried by the runtime

    Important precedence rule:
    installed config defaults < route defaults < router constructor defaults <
    explicit per-call overrides

    Important boundary rule:
    this facade owns caller-facing shape and precedence semantics, while all
    retry, limiter, fallback, timeout, provider adaptation, and tracing logic
    stays in the private runtime.
    """

    def __init__(  # noqa: PLR0913
        self,
        spec: Model | RouterProfile | Sequence[RouterProfile],
        *,
        session: Session | None = None,
        key_id: KeyId | None = None,
        temperature: float | None = None,
        seed: int | None = None,
        response_schema: type[BaseModel] | dict[str, Any] | None = None,
        tools: Sequence[Callable[..., Any] | dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        max_tool_rounds: int | None = None,
        max_attempts: int | None = None,
        attempt_timeout_seconds: float | None = None,
        wait_for_cooldown_if_all_blocked: bool | None = None,
        round_robin_start: bool | None = None,
        shuffle_fallbacks: bool | None = None,
        default_limits: ProviderLimits | None = None,
        limits_by_provider: dict[Provider, ProviderLimits] | None = None,
        **kwargs: object,
    ) -> None:
        """Create a router facade bound to one private runtime.

        Args:
            spec:
                Route intent for this router. Use a `Model` for the simplest
                case, a `RouterProfile` for a pinned route, or a sequence of
                profiles for fallback routing.
            session:
                Optional conversation state shared across requests from this
                router instance.
            key_id:
                Optional reusable key selection override. Use an integer to pin
                one key or `"auto"` to let the runtime rotate across discovered
                keys for that provider.
            temperature:
                Reusable temperature default for this router.
            seed:
                Reusable generation seed default for this router.
            response_schema:
                Optional reusable structured-output schema.
            tools:
                Optional reusable local tool set exposed to tool-capable
                providers.
            tool_choice:
                Optional reusable tool-choice policy or forced-tool selection.
            max_tool_rounds:
                Reusable cap on tool-calling rounds for one request.
            max_attempts:
                Optional cap on how many concrete routes the runtime may try.
            attempt_timeout_seconds:
                Optional per-attempt timeout enforced by the router runtime.
            wait_for_cooldown_if_all_blocked:
                Whether the runtime may wait for the earliest cooldown to
                expire when every route is currently blocked.
            round_robin_start:
                Whether repeated requests should rotate the starting route.
            shuffle_fallbacks:
                Whether fallback routes may be shuffled after the starting
                route is chosen.
            default_limits:
                Shared limiter defaults applied to providers without a more
                specific provider override.
            limits_by_provider:
                Optional per-provider limiter overrides.
            **kwargs:
                Extra provider-specific request kwargs forwarded into the
                runtime. This is the escape hatch for provider features that do
                not have a dedicated top-level public field.
        """
        self._runtime = RouterRuntime(
            spec=spec,
            session=None if session is None else session._store,
            key_id=key_id,
            temperature=temperature,
            seed=seed,
            response_schema=response_schema,
            tools=tools,
            tool_choice=tool_choice,
            max_tool_rounds=max_tool_rounds,
            max_attempts=max_attempts,
            attempt_timeout_seconds=attempt_timeout_seconds,
            wait_for_cooldown_if_all_blocked=wait_for_cooldown_if_all_blocked,
            round_robin_start=round_robin_start,
            shuffle_fallbacks=shuffle_fallbacks,
            default_limits=default_limits,
            limits_by_provider=limits_by_provider,
            **kwargs,
        )

    def query(  # noqa: PLR0913
        self,
        content: str | MessageContent,
        *,
        temperature: float | None | _CallUnset = CALL_UNSET,
        seed: int | None | _CallUnset = CALL_UNSET,
        response_schema: (
            type[BaseModel] | dict[str, Any] | None | _CallUnset
        ) = CALL_UNSET,
        tools: (
            Sequence[Callable[..., Any] | dict[str, Any]] | None | _CallUnset
        ) = CALL_UNSET,
        tool_choice: str | dict[str, Any] | None | _CallUnset = CALL_UNSET,
        max_tool_rounds: int | _CallUnset = CALL_UNSET,
        **kwargs: object,
    ) -> LLMRouterResponse:
        """Execute one synchronous request and return the normalized response.

        `content` accepts either a single string or role-less multimodal
        `MessageContent`. The runtime turns that public input into whatever the
        selected provider requires.

        Only explicit per-call overrides are forwarded. If a field is omitted,
        the router keeps using the layered defaults already attached to the
        route and router.
        """
        runtime_kwargs = _build_call_kwargs(
            kwargs=kwargs,
            overrides=(
                ("temperature", temperature),
                ("seed", seed),
                ("response_schema", response_schema),
                ("tools", tools),
                ("tool_choice", tool_choice),
                ("max_tool_rounds", max_tool_rounds),
            ),
        )
        return self._runtime.query(content, **runtime_kwargs)

    async def aquery(  # noqa: PLR0913
        self,
        content: str | MessageContent,
        *,
        temperature: float | None | _CallUnset = CALL_UNSET,
        seed: int | None | _CallUnset = CALL_UNSET,
        response_schema: (
            type[BaseModel] | dict[str, Any] | None | _CallUnset
        ) = CALL_UNSET,
        tools: (
            Sequence[Callable[..., Any] | dict[str, Any]] | None | _CallUnset
        ) = CALL_UNSET,
        tool_choice: str | dict[str, Any] | None | _CallUnset = CALL_UNSET,
        max_tool_rounds: int | _CallUnset = CALL_UNSET,
        **kwargs: object,
    ) -> LLMRouterResponse:
        """Execute one asynchronous request and return the normalized response.

        This has the same public semantics as `query()`, but runs through the
        async runtime path and provider clients.
        """
        runtime_kwargs = _build_call_kwargs(
            kwargs=kwargs,
            overrides=(
                ("temperature", temperature),
                ("seed", seed),
                ("response_schema", response_schema),
                ("tools", tools),
                ("tool_choice", tool_choice),
                ("max_tool_rounds", max_tool_rounds),
            ),
        )
        return await self._runtime.aquery(content, **runtime_kwargs)

"""Provider execution pipeline for resolved routes.

Why:
    Owns the private cutover from router-selected routes to provider adapter
    calls, same-route retry, local tool loops, structured-output repair, and
    public response assembly.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from typing import Any

from py_lib_runtime import get_logger, log_retry_exhausted, preview_value

from llm_router._api.errors import LLMRouterError, ProviderError, ToolExecutionError
from llm_router._api.types import LLMRouterResponse, Provider
from llm_router._internal.capabilities.content import (
    NormalizedMessage,
    normalize_content,
)
from llm_router._internal.capabilities.schema import (
    SchemaSpec,
    normalize_schema,
    validate_schema_output,
)
from llm_router._internal.capabilities.tools import (
    ToolChoice,
    ToolLoopState,
    ToolRegistry,
    run_tool_round,
)
from llm_router._internal.config import LLMRouterConfig
from llm_router._internal.providers.base import (
    ProviderAdapter,
    ProviderCredential,
    ProviderRequest,
    ProviderResult,
)
from llm_router._internal.providers.registry import get_adapter
from llm_router._internal.providers.retry import (
    build_provider_async_retrying,
    build_provider_retrying,
    is_retryable_provider_error,
)
from llm_router._internal.runtime.output import build_public_response
from llm_router._internal.runtime.requests import ResolvedRequest
from llm_router._internal.runtime.tracing import (
    append_repair_message,
    append_tool_result_message,
    next_tool_choice_after_tool_round,
    structured_output_error,
)

logger = get_logger(__name__)

AdapterGetter = Callable[[Provider, LLMRouterConfig], ProviderAdapter]


@dataclass(frozen=True, slots=True)
class _ExecutionPlan:
    """Normalized execution settings for one resolved route."""

    schema: SchemaSpec | None
    tool_registry: ToolRegistry | None
    tool_choice: ToolChoice | None
    max_tool_rounds: int


@dataclass(frozen=True, slots=True)
class _ExecutionLoopState:
    """Mutable-by-replacement state for one provider execution loop."""

    messages: tuple[NormalizedMessage, ...]
    tool_state: ToolLoopState
    tool_choice: ToolChoice | None
    tool_registry: ToolRegistry | None
    schema: SchemaSpec | None
    structured_attempts: int


@dataclass(frozen=True, slots=True)
class _ResultStep:
    """One provider-result transition, optionally ending in a response."""

    state: _ExecutionLoopState
    response: LLMRouterResponse | None = None


class ProviderRouteExecutor:
    """Execute one resolved route through the provider adapter port."""

    def __init__(
        self,
        *,
        config: LLMRouterConfig,
        adapter_getter: AdapterGetter | None = None,
    ) -> None:
        """Create an executor bound to one immutable runtime config."""
        self._config = config
        self._adapter_getter = adapter_getter or _default_adapter_getter

    def execute(self, request: ResolvedRequest) -> LLMRouterResponse:
        """Execute one synchronous resolved request."""
        plan = _build_execution_plan(request=request)
        state = _initial_loop_state(request=request, plan=plan)

        while True:
            provider_request = _provider_request_from_state(
                request=request,
                state=state,
            )
            result = self._execute_provider_sync(provider_request)
            step = _advance_after_result(
                config=self._config,
                provider_request=provider_request,
                plan=plan,
                state=state,
                result=result,
            )
            if step.response is not None:
                return step.response
            state = step.state

    async def aexecute(self, request: ResolvedRequest) -> LLMRouterResponse:
        """Execute one asynchronous resolved request."""
        plan = _build_execution_plan(request=request)
        state = _initial_loop_state(request=request, plan=plan)

        while True:
            provider_request = _provider_request_from_state(
                request=request,
                state=state,
            )
            result = await self._execute_provider_async(provider_request)
            step = _advance_after_result(
                config=self._config,
                provider_request=provider_request,
                plan=plan,
                state=state,
                result=result,
            )
            if step.response is not None:
                return step.response
            state = step.state

    def _execute_provider_sync(self, request: ProviderRequest) -> ProviderResult:
        """Run one provider call with same-route retry."""
        adapter = self._adapter_for(request)
        retrying = build_provider_retrying(
            policy=self._config.retry_policy,
            logger=logger,
            context_getter=lambda: _retry_context(request),
        )
        try:
            for attempt in retrying:
                with attempt:
                    return adapter.execute(request)
        except Exception as exc:
            if is_retryable_provider_error(exc):
                log_retry_exhausted(
                    logger,
                    error=exc,
                    event_type="llm_router.provider.retry.exhausted",
                    context=_retry_context(request),
                )
            raise _provider_boundary_error(exc, request=request) from exc
        msg = "Provider retry loop ended without a result."
        raise RuntimeError(msg)

    async def _execute_provider_async(self, request: ProviderRequest) -> ProviderResult:
        """Run one async provider call with same-route retry."""
        adapter = self._adapter_for(request)
        retrying = build_provider_async_retrying(
            policy=self._config.retry_policy,
            logger=logger,
            context_getter=lambda: _retry_context(request),
        )
        try:
            async for attempt in retrying:
                with attempt:
                    return await adapter.aexecute(request)
        except Exception as exc:
            if is_retryable_provider_error(exc):
                log_retry_exhausted(
                    logger,
                    error=exc,
                    event_type="llm_router.provider.retry.exhausted",
                    context=_retry_context(request),
                )
            raise _provider_boundary_error(exc, request=request) from exc
        msg = "Provider retry loop ended without a result."
        raise RuntimeError(msg)

    def _adapter_for(self, request: ProviderRequest) -> ProviderAdapter:
        """Return the adapter selected for one provider request."""
        return self._adapter_getter(request.provider, self._config)


@dataclass(frozen=True, slots=True)
class _StructuredValidation:
    """Structured-output validation outcome for executor flow control."""

    valid: bool
    value: object | None = None
    error_message: str | None = None


def _default_adapter_getter(
    provider: Provider,
    config: LLMRouterConfig,
) -> ProviderAdapter:
    """Resolve provider adapters through the shared registry."""
    return get_adapter(provider=provider, config=config)


def _build_execution_plan(*, request: ResolvedRequest) -> _ExecutionPlan:
    """Normalize execution settings once per resolved route."""
    schema = (
        None
        if request.settings.response_schema is None
        else normalize_schema(request.settings.response_schema)
    )
    registry = (
        None
        if not request.settings.tools
        else ToolRegistry.from_tools(request.settings.tools)
    )
    tool_choice = (
        None
        if request.settings.tool_choice is None
        else _normalize_tool_choice(
            choice=request.settings.tool_choice,
            registry=registry,
        )
    )
    max_tool_rounds = request.settings.max_tool_rounds
    return _ExecutionPlan(
        schema=schema,
        tool_registry=registry,
        tool_choice=tool_choice,
        max_tool_rounds=0 if max_tool_rounds is None else max(0, int(max_tool_rounds)),
    )


def _normalize_tool_choice(
    *,
    choice: str | dict[str, Any],
    registry: ToolRegistry | None,
) -> ToolChoice:
    """Normalize a tool choice without importing the helper at module top level."""
    from llm_router._internal.capabilities.tools import normalize_tool_choice

    return normalize_tool_choice(choice, registry=registry)


def _initial_messages(request: ResolvedRequest) -> tuple[NormalizedMessage, ...]:
    """Return the initial user turn as one normalized provider message."""
    if _is_direct_text_sequence(request):
        return tuple(normalize_content(message) for message in request.messages)
    return (normalize_content(request.messages),)


def _is_direct_text_sequence(request: ResolvedRequest) -> bool:
    """Return whether a role-less text sequence should preserve message turns."""
    if isinstance(request.content, str):
        return False
    if not isinstance(request.content, Sequence):
        return False
    if isinstance(request.content, bytes | bytearray):
        return False
    content_parts = tuple(request.content)
    return content_parts == request.messages and all(
        isinstance(part, str) for part in content_parts
    )


def _initial_provider_schema(
    *,
    request: ResolvedRequest,
    plan: _ExecutionPlan,
) -> SchemaSpec | None:
    """Return schema advertised on the first provider turn."""
    if plan.tool_registry is None or not _schema_waits_for_tool_completion(
        request.route.provider
    ):
        return plan.schema
    return None


def _initial_loop_state(
    *,
    request: ResolvedRequest,
    plan: _ExecutionPlan,
) -> _ExecutionLoopState:
    """Return the first provider-loop state for one resolved request."""
    return _ExecutionLoopState(
        messages=_initial_messages(request),
        tool_state=ToolLoopState(max_rounds=plan.max_tool_rounds),
        tool_choice=plan.tool_choice,
        tool_registry=plan.tool_registry,
        schema=_initial_provider_schema(request=request, plan=plan),
        structured_attempts=0,
    )


def _schema_waits_for_tool_completion(provider: Provider) -> bool:
    """Return whether a provider should receive schema only after tool turns."""
    return provider in {Provider.AISTUDIO, Provider.GOOGLE}


def _provider_request_from_state(
    *,
    request: ResolvedRequest,
    state: _ExecutionLoopState,
) -> ProviderRequest:
    """Build an adapter request from the current execution-loop state."""
    return _provider_request(
        request=request,
        messages=state.messages,
        schema=state.schema,
        tool_registry=state.tool_registry,
        tool_choice=state.tool_choice,
    )


def _provider_request(
    *,
    request: ResolvedRequest,
    messages: Sequence[NormalizedMessage],
    schema: SchemaSpec | None,
    tool_registry: ToolRegistry | None,
    tool_choice: ToolChoice | None,
) -> ProviderRequest:
    """Build the provider-neutral adapter request for one model turn."""
    return ProviderRequest(
        request_id=request.request_id,
        provider=request.route.provider,
        model=request.route.model,
        provider_model=request.route.provider_model,
        credential=ProviderCredential(
            key_id=request.key.key_id,
            env_var=request.key.env_var,
            value=request.key.value,
        ),
        messages=messages,
        temperature=request.settings.temperature,
        seed=request.settings.seed,
        schema=schema,
        tool_registry=tool_registry,
        tool_choice=tool_choice,
        kwargs=request.settings.kwargs,
        route_index=request.route.route_index,
    )


def _advance_after_result(
    *,
    config: LLMRouterConfig,
    provider_request: ProviderRequest,
    plan: _ExecutionPlan,
    state: _ExecutionLoopState,
    result: ProviderResult,
) -> _ResultStep:
    """Advance the execution loop after one provider result."""
    tool_step = _advance_tool_result(
        provider_request=provider_request,
        plan=plan,
        state=state,
        result=result,
    )
    if tool_step is not None:
        return tool_step
    return _advance_structured_result(
        config=config,
        provider_request=provider_request,
        plan=plan,
        state=state,
        result=result,
    )


def _advance_tool_result(
    *,
    provider_request: ProviderRequest,
    plan: _ExecutionPlan,
    state: _ExecutionLoopState,
    result: ProviderResult,
) -> _ResultStep | None:
    """Handle a provider result containing tool calls, when present."""
    if not result.tool_calls:
        return None
    if plan.tool_registry is None:
        return _ResultStep(
            state=state,
            response=build_public_response(
                result,
                tool_trace=state.tool_state.steps,
            ),
        )

    next_tool_state = _run_logged_tool_round(
        request=provider_request,
        state=state.tool_state,
        result=result,
        registry=plan.tool_registry,
    )
    if _tool_limit_reached(state=next_tool_state, result=result):
        _log_tool_round_limit(request=provider_request, state=next_tool_state)
        return _ResultStep(
            state=state,
            response=build_public_response(
                result,
                output_text="",
                tool_calls=result.tool_calls,
                tool_trace=next_tool_state.steps,
            ),
        )
    return _ResultStep(
        state=replace(
            state,
            messages=append_tool_result_message(
                state.messages,
                next_tool_state.steps[len(state.tool_state.steps) :],
                all_steps=next_tool_state.steps,
                request=provider_request,
                result=result,
            ),
            tool_state=next_tool_state,
            tool_choice=next_tool_choice_after_tool_round(
                provider=provider_request.provider,
                tool_choice=plan.tool_choice,
            ),
        )
    )


def _advance_structured_result(
    *,
    config: LLMRouterConfig,
    provider_request: ProviderRequest,
    plan: _ExecutionPlan,
    state: _ExecutionLoopState,
    result: ProviderResult,
) -> _ResultStep:
    """Handle structured-output validation and repair loop state."""
    validated = _validate_structured_result(
        request=provider_request,
        plan=plan,
        result=result,
        completed_attempts=state.structured_attempts,
    )
    if validated.valid:
        return _ResultStep(
            state=state,
            response=build_public_response(
                result,
                tool_trace=state.tool_state.steps,
                structured_data=validated.value,
            ),
        )

    next_attempts = state.structured_attempts + 1
    error_message = validated.error_message or "Validation failed."
    if next_attempts >= config.structured_output_max_attempts:
        _log_schema_repair_exhausted(
            request=provider_request,
            plan=plan,
            error_message=error_message,
        )
        raise structured_output_error(result=result, message=error_message)

    _log_schema_repair_started(
        request=provider_request,
        plan=plan,
        error_message=error_message,
    )
    return _ResultStep(
        state=replace(
            state,
            messages=append_repair_message(
                state.messages,
                request=provider_request,
                schema=plan.schema,
                result=result,
                error_message=error_message,
            ),
            schema=plan.schema,
            tool_registry=None,
            tool_choice=None,
            structured_attempts=next_attempts,
        )
    )


def _tool_limit_reached(
    *,
    state: ToolLoopState,
    result: ProviderResult,
) -> bool:
    """Return whether the current tool-call result exhausted local rounds."""
    return bool(result.tool_calls) and state.completed_rounds >= state.max_rounds


def _validate_structured_result(
    *,
    request: ProviderRequest,
    plan: _ExecutionPlan,
    result: ProviderResult,
    completed_attempts: int,
) -> _StructuredValidation:
    """Validate structured output or report that no schema is active."""
    if plan.schema is None:
        return _StructuredValidation(valid=True)
    validation = validate_schema_output(plan.schema, result.output_text)
    if validation.valid and completed_attempts:
        _log_schema_repair_succeeded(request=request, plan=plan)
    if not validation.valid:
        _log_schema_validation_failed(
            request=request,
            plan=plan,
            error_message=validation.error_message or "Validation failed.",
        )
    return _StructuredValidation(
        valid=validation.valid,
        value=validation.value,
        error_message=validation.error_message,
    )


def _run_logged_tool_round(
    *,
    request: ProviderRequest,
    state: ToolLoopState,
    result: ProviderResult,
    registry: ToolRegistry,
) -> ToolLoopState:
    """Run one tool round and emit safe tool observability events."""
    if state.can_execute_tools():
        for call in result.tool_calls:
            _log_tool_called(request=request, state=state, tool_name=call.name)
    try:
        next_state = run_tool_round(
            state=state,
            tool_calls=result.tool_calls,
            registry=registry,
        )
    except ToolExecutionError as exc:
        _log_tool_failed(request=request, state=state, error=exc)
        raise
    for step in next_state.steps[len(state.steps) :]:
        _log_tool_completed(request=request, state=state, tool_name=step.tool_name)
    return next_state


def _provider_boundary_error(
    exc: Exception,
    *,
    request: ProviderRequest,
) -> Exception:
    """Translate private/provider failures at the provider execution boundary."""
    if isinstance(exc, LLMRouterError):
        return exc
    return ProviderError(exc, request.provider, request.model)


def _retry_context(request: ProviderRequest) -> dict[str, Any]:
    """Return safe retry log fields for one provider request."""
    return request.log_context()


def _log_schema_validation_failed(
    *,
    request: ProviderRequest,
    plan: _ExecutionPlan,
    error_message: str,
) -> None:
    """Log one structured-output validation miss without raw output."""
    logger.warning(
        "Schema validation failed",
        event_type="llm_router.capability.schema.validation.failed",
        **_retry_context(request),
        schema_name=None if plan.schema is None else plan.schema.name,
        error_message=preview_value(error_message),
    )


def _log_schema_repair_started(
    *,
    request: ProviderRequest,
    plan: _ExecutionPlan,
    error_message: str,
) -> None:
    """Log one structured-output repair attempt."""
    logger.info(
        "Schema repair started",
        event_type="llm_router.capability.schema.repair.started",
        **_retry_context(request),
        schema_name=None if plan.schema is None else plan.schema.name,
        error_message=preview_value(error_message),
    )


def _log_schema_repair_succeeded(
    *,
    request: ProviderRequest,
    plan: _ExecutionPlan,
) -> None:
    """Log successful structured-output repair."""
    logger.info(
        "Schema repair succeeded",
        event_type="llm_router.capability.schema.repair.succeeded",
        **_retry_context(request),
        schema_name=None if plan.schema is None else plan.schema.name,
    )


def _log_schema_repair_exhausted(
    *,
    request: ProviderRequest,
    plan: _ExecutionPlan,
    error_message: str,
) -> None:
    """Log exhausted structured-output repair."""
    logger.warning(
        "Schema repair exhausted",
        event_type="llm_router.capability.schema.repair.exhausted",
        **_retry_context(request),
        schema_name=None if plan.schema is None else plan.schema.name,
        error_message=preview_value(error_message),
    )


def _log_tool_called(
    *,
    request: ProviderRequest,
    state: ToolLoopState,
    tool_name: str,
) -> None:
    """Log a local tool call without arguments."""
    logger.info(
        "Tool called",
        event_type="llm_router.capability.tool.called",
        **_retry_context(request),
        tool_round=state.completed_rounds + 1,
        tool_name=tool_name,
    )


def _log_tool_completed(
    *,
    request: ProviderRequest,
    state: ToolLoopState,
    tool_name: str,
) -> None:
    """Log a completed local tool call without result payloads."""
    logger.info(
        "Tool completed",
        event_type="llm_router.capability.tool.completed",
        **_retry_context(request),
        tool_round=state.completed_rounds + 1,
        tool_name=tool_name,
    )


def _log_tool_failed(
    *,
    request: ProviderRequest,
    state: ToolLoopState,
    error: ToolExecutionError,
) -> None:
    """Log a local tool failure without raw argument payloads."""
    logger.warning(
        "Tool failed",
        event_type="llm_router.capability.tool.failed",
        **_retry_context(request),
        tool_round=state.completed_rounds + 1,
        tool_name=error.tool_name,
        error_type=type(error).__name__,
        error_message=preview_value(str(error)),
    )


def _log_tool_round_limit(
    *,
    request: ProviderRequest,
    state: ToolLoopState,
) -> None:
    """Log a local tool-loop round limit stop."""
    logger.warning(
        "Tool round limit reached",
        event_type="llm_router.capability.tool.round_limit_reached",
        **_retry_context(request),
        tool_round=state.completed_rounds,
    )

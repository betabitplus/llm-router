"""Private router runtime facade.

Why:
    Provides the private object consumed by `llm_router._api.router.LLMRouter`
    while later phases fill in routing, fallback, provider execution, and
    response assembly.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from concurrent.futures import (
    ThreadPoolExecutor,
    TimeoutError as FutureTimeoutError,
)
from dataclasses import dataclass
from time import sleep

from py_lib_runtime import get_logger, preview_exception_message

from llm_router._api.types import ChatPart, LLMRouterResponse, Provider, RoutingAttempt
from llm_router._internal.config import get_config
from llm_router._internal.runtime.effective_settings import (
    EffectiveSettings,
    resolve_effective_settings,
    split_router_defaults,
)
from llm_router._internal.runtime.errors import RouteBlockedError
from llm_router._internal.runtime.executor import ProviderRouteExecutor
from llm_router._internal.runtime.ids import next_request_id
from llm_router._internal.runtime.limiter import KeyResolver, LimiterState
from llm_router._internal.runtime.requests import ResolvedRequest, RouteExecutor
from llm_router._internal.runtime.routes import (
    ExpandedRoute,
    RouteOrderOptions,
    expand_route_plan,
    ordered_routes,
)
from llm_router._internal.runtime.tracing import build_attempt_trace

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class _BlockedRequest:
    """Route request deferred by limiter state."""

    request: ResolvedRequest
    wait_seconds: float


class RouterRuntime:
    """Private runtime object behind the public `LLMRouter` facade."""

    def __init__(
        self,
        *,
        spec: object,
        session: object | None = None,
        **kwargs: object,
    ) -> None:
        """Capture constructor inputs for later runtime phases."""
        self.config = get_config()
        self.spec = spec
        self.session = session
        self._executor = _pop_executor(kwargs) or ProviderRouteExecutor(
            config=self.config,
        )
        self.router_defaults = split_router_defaults(kwargs)
        self.route_plan = expand_route_plan(spec, config=self.config)
        self._log_routes_expanded()
        self._limiter = LimiterState()
        self._keys = KeyResolver(self.config)
        self._request_index = 0

    def query(self, content: object, **runtime_kwargs: object) -> object:
        """Execute one synchronous request."""
        return self._run_sync(content=content, call_overrides=runtime_kwargs)

    async def aquery(self, content: object, **runtime_kwargs: object) -> object:
        """Execute one asynchronous request."""
        return await self._run_async(content=content, call_overrides=runtime_kwargs)

    def _next_attempt_order(
        self, *, settings: EffectiveSettings
    ) -> tuple[ExpandedRoute, ...]:
        """Return route attempt order and advance the round-robin cursor."""
        request_index = self._request_index
        self._request_index += 1
        return ordered_routes(
            self.route_plan,
            options=RouteOrderOptions(
                round_robin_start=settings.round_robin_start,
                shuffle_fallbacks=settings.shuffle_fallbacks,
                min_routes_for_fallback_shuffle=(
                    self.config.policy.min_routes_for_fallback_shuffle
                ),
                request_index=request_index,
                max_attempts=settings.max_attempts,
            ),
        )

    def _run_sync(
        self,
        *,
        content: object,
        call_overrides: dict[str, object],
    ) -> object:
        """Run provider-neutral sync routing with fallback traces."""
        request_id = next_request_id()
        self._log_request_started(request_id=request_id)
        last_error: Exception | None = None
        failed_traces: list[RoutingAttempt] = []
        blocked_requests: list[_BlockedRequest] = []
        first_settings = self._settings_for_first_route(call_overrides=call_overrides)
        for route in self._next_attempt_order(settings=first_settings):
            settings = self._settings_for_route(
                route=route, call_overrides=call_overrides
            )
            self._log_route_selected(request_id=request_id, route=route)
            try:
                request, wait_seconds = self._prepare_request(
                    request_id=request_id,
                    route=route,
                    settings=settings,
                    content=content,
                )
            except Exception as exc:
                last_error = exc
                self._log_attempt_failed(
                    request_id=request_id,
                    route=route,
                    error=exc,
                )
                failed_traces.append(
                    self._trace_error(route=route, settings=settings, error=exc)
                )
                continue
            if wait_seconds > 0:
                blocked_requests.append(
                    _BlockedRequest(request=request, wait_seconds=wait_seconds)
                )
                self._log_route_blocked(
                    request_id=request_id,
                    request=request,
                    wait_seconds=wait_seconds,
                )
                continue
            try:
                self._log_attempt_started(request_id=request_id, request=request)
                response = self._call_sync_with_timeout(
                    request,
                    timeout_seconds=settings.attempt_timeout_seconds,
                )
            except Exception as exc:
                last_error = exc
                self._record_failure(request=request, exc=exc)
                self._log_attempt_failed(
                    request_id=request_id,
                    route=route,
                    error=exc,
                )
                failed_traces.append(
                    build_attempt_trace(
                        route=route,
                        settings=settings,
                        key_id=request.key.key_id,
                        error=exc,
                    )
                )
                continue
            self._record_success(route=route, settings=settings, request=request)
            self._log_attempt_succeeded(request_id=request_id, request=request)
            trace = build_attempt_trace(
                route=route,
                settings=settings,
                key_id=request.key.key_id,
                wait_seconds=wait_seconds,
            )
            return self._complete_success(
                content=content,
                request_id=request_id,
                response=response,
                traces=[*failed_traces, *self._blocked_traces(blocked_requests)],
                final_trace=trace,
            )
        if blocked_requests:
            return self._run_blocked_sync(
                content=content,
                request_id=request_id,
                blocked_requests=blocked_requests,
                failed_traces=failed_traces,
                last_error=last_error,
            )
        if last_error is None:
            msg = "No route attempts were available."
            raise TimeoutError(msg)
        self._log_request_failed(request_id=request_id, error=last_error)
        raise last_error

    async def _run_async(
        self,
        *,
        content: object,
        call_overrides: dict[str, object],
    ) -> object:
        """Run provider-neutral async routing with fallback traces."""
        request_id = next_request_id()
        self._log_request_started(request_id=request_id)
        last_error: Exception | None = None
        failed_traces: list[RoutingAttempt] = []
        blocked_requests: list[_BlockedRequest] = []
        first_settings = self._settings_for_first_route(call_overrides=call_overrides)
        for route in self._next_attempt_order(settings=first_settings):
            settings = self._settings_for_route(
                route=route, call_overrides=call_overrides
            )
            self._log_route_selected(request_id=request_id, route=route)
            try:
                request, wait_seconds = self._prepare_request(
                    request_id=request_id,
                    route=route,
                    settings=settings,
                    content=content,
                )
            except Exception as exc:
                last_error = exc
                self._log_attempt_failed(
                    request_id=request_id,
                    route=route,
                    error=exc,
                )
                failed_traces.append(
                    self._trace_error(route=route, settings=settings, error=exc)
                )
                continue
            if wait_seconds > 0:
                blocked_requests.append(
                    _BlockedRequest(request=request, wait_seconds=wait_seconds)
                )
                self._log_route_blocked(
                    request_id=request_id,
                    request=request,
                    wait_seconds=wait_seconds,
                )
                continue
            try:
                self._log_attempt_started(request_id=request_id, request=request)
                response = await self._call_async_with_timeout(
                    request,
                    timeout_seconds=settings.attempt_timeout_seconds,
                )
            except Exception as exc:
                last_error = exc
                self._record_failure(request=request, exc=exc)
                self._log_attempt_failed(
                    request_id=request_id,
                    route=route,
                    error=exc,
                )
                failed_traces.append(
                    build_attempt_trace(
                        route=route,
                        settings=settings,
                        key_id=request.key.key_id,
                        error=exc,
                    )
                )
                continue
            self._record_success(route=route, settings=settings, request=request)
            self._log_attempt_succeeded(request_id=request_id, request=request)
            trace = build_attempt_trace(
                route=route,
                settings=settings,
                key_id=request.key.key_id,
                wait_seconds=wait_seconds,
            )
            return self._complete_success(
                content=content,
                request_id=request_id,
                response=response,
                traces=[*failed_traces, *self._blocked_traces(blocked_requests)],
                final_trace=trace,
            )
        if blocked_requests:
            return await self._run_blocked_async(
                content=content,
                request_id=request_id,
                blocked_requests=blocked_requests,
                failed_traces=failed_traces,
                last_error=last_error,
            )
        if last_error is None:
            msg = "No route attempts were available."
            raise TimeoutError(msg)
        self._log_request_failed(request_id=request_id, error=last_error)
        raise last_error

    def _settings_for_first_route(
        self,
        *,
        call_overrides: dict[str, object],
    ) -> EffectiveSettings:
        """Resolve settings against the first route for ordering policy."""
        first_route = self.route_plan.routes[0]
        return self._settings_for_route(
            route=first_route, call_overrides=call_overrides
        )

    def _settings_for_route(
        self,
        *,
        route: ExpandedRoute,
        call_overrides: dict[str, object],
    ) -> EffectiveSettings:
        """Resolve settings for one route."""
        return resolve_effective_settings(
            config=self.config,
            route_defaults=route.defaults,
            route_policy_defaults=self.route_plan.policy_defaults,
            router_defaults=self.router_defaults,
            call_overrides=call_overrides,
        )

    def _prepare_request(
        self,
        *,
        request_id: str,
        route: ExpandedRoute,
        settings: EffectiveSettings,
        content: object,
    ) -> tuple[ResolvedRequest, float]:
        """Build one provider-neutral request and apply limiter waiting."""
        if not isinstance(route.provider, Provider):
            msg = f"Unknown provider: {route.provider}"
            raise ValueError(msg)  # noqa: TRY004
        key = self._keys.resolve(provider=route.provider, key_id=settings.key_id)
        wait_seconds = self._limiter.wait_seconds(
            provider=route.provider,
            key_id=key.key_id,
        )
        if wait_seconds > 0:
            logger.info(
                "Route blocked by limit",
                event_type="llm_router.routing.limit.blocked",
                request_id=request_id,
                provider=route.provider.value,
                route_index=route.route_index,
                key_id=key.key_id,
                wait_seconds=wait_seconds,
            )
        messages = self._messages_for_content(content)
        return (
            ResolvedRequest(
                request_id=request_id,
                route=route,
                settings=settings,
                key=key,
                messages=messages,
                content=content,
            ),
            wait_seconds,
        )

    def _call_sync_with_timeout(
        self,
        request: ResolvedRequest,
        *,
        timeout_seconds: float | None,
    ) -> LLMRouterResponse:
        """Run one sync executor attempt with optional timeout."""
        if timeout_seconds is None:
            return self._executor.execute(request)
        pool = ThreadPoolExecutor(max_workers=1)
        future = pool.submit(self._executor.execute, request)
        timed_out = False
        try:
            return future.result(timeout=timeout_seconds)
        except FutureTimeoutError as exc:
            timed_out = True
            future.cancel()
            msg = "Attempt timed out."
            raise TimeoutError(msg) from exc
        finally:
            pool.shutdown(wait=not timed_out, cancel_futures=True)

    async def _call_async_with_timeout(
        self,
        request: ResolvedRequest,
        *,
        timeout_seconds: float | None,
    ) -> LLMRouterResponse:
        """Run one async executor attempt with optional timeout."""
        coro = self._executor.aexecute(request)
        if timeout_seconds is None:
            return await coro
        return await asyncio.wait_for(coro, timeout=timeout_seconds)

    def _record_success(
        self,
        *,
        route: ExpandedRoute,
        settings: EffectiveSettings,
        request: ResolvedRequest,
    ) -> None:
        """Record limiter state after a successful attempt."""
        limits = settings.limits_by_provider.get(route.provider)
        if limits is None:
            limits = settings.default_limits
        self._limiter.record_success(
            provider=route.provider,
            key_id=request.key.key_id,
            limits=limits,
        )

    def _record_failure(
        self,
        *,
        request: ResolvedRequest,
        exc: Exception,
    ) -> None:
        """Record limiter state after a failed attempt."""
        del exc
        route = request.route
        settings = request.settings
        limits = settings.limits_by_provider.get(route.provider)
        if limits is None:
            limits = settings.default_limits
        self._limiter.record_failure(
            provider=route.provider,
            key_id=request.key.key_id,
            limits=limits,
        )

    def _run_blocked_sync(
        self,
        *,
        content: object,
        request_id: str,
        blocked_requests: Sequence[_BlockedRequest],
        failed_traces: Sequence[RoutingAttempt],
        last_error: Exception | None,
    ) -> LLMRouterResponse:
        """Run or fail an all-blocked sync route set."""
        selected = self._select_blocked_request(blocked_requests)
        if not selected.request.settings.wait_for_cooldown_if_all_blocked:
            error = self._all_blocked_error()
            self._log_request_failed(request_id=request_id, error=error)
            raise error from last_error
        self._wait_for_blocked_request(request_id=request_id, blocked=selected)
        try:
            self._log_attempt_started(request_id=request_id, request=selected.request)
            response = self._call_sync_with_timeout(
                selected.request,
                timeout_seconds=selected.request.settings.attempt_timeout_seconds,
            )
        except Exception as exc:
            self._record_failure(request=selected.request, exc=exc)
            self._log_request_failed(request_id=request_id, error=exc)
            raise
        self._record_success(
            route=selected.request.route,
            settings=selected.request.settings,
            request=selected.request,
        )
        self._log_attempt_succeeded(request_id=request_id, request=selected.request)
        trace = build_attempt_trace(
            route=selected.request.route,
            settings=selected.request.settings,
            key_id=selected.request.key.key_id,
            wait_seconds=selected.wait_seconds,
        )
        return self._complete_success(
            content=content,
            request_id=request_id,
            response=response,
            traces=failed_traces,
            final_trace=trace,
        )

    async def _run_blocked_async(
        self,
        *,
        content: object,
        request_id: str,
        blocked_requests: Sequence[_BlockedRequest],
        failed_traces: Sequence[RoutingAttempt],
        last_error: Exception | None,
    ) -> LLMRouterResponse:
        """Run or fail an all-blocked async route set."""
        selected = self._select_blocked_request(blocked_requests)
        if not selected.request.settings.wait_for_cooldown_if_all_blocked:
            error = self._all_blocked_error()
            self._log_request_failed(request_id=request_id, error=error)
            raise error from last_error
        await self._wait_for_blocked_request_async(
            request_id=request_id,
            blocked=selected,
        )
        try:
            self._log_attempt_started(request_id=request_id, request=selected.request)
            response = await self._call_async_with_timeout(
                selected.request,
                timeout_seconds=selected.request.settings.attempt_timeout_seconds,
            )
        except Exception as exc:
            self._record_failure(request=selected.request, exc=exc)
            self._log_request_failed(request_id=request_id, error=exc)
            raise
        self._record_success(
            route=selected.request.route,
            settings=selected.request.settings,
            request=selected.request,
        )
        self._log_attempt_succeeded(request_id=request_id, request=selected.request)
        trace = build_attempt_trace(
            route=selected.request.route,
            settings=selected.request.settings,
            key_id=selected.request.key.key_id,
            wait_seconds=selected.wait_seconds,
        )
        return self._complete_success(
            content=content,
            request_id=request_id,
            response=response,
            traces=failed_traces,
            final_trace=trace,
        )

    def _select_blocked_request(
        self,
        blocked_requests: Sequence[_BlockedRequest],
    ) -> _BlockedRequest:
        """Return the blocked route with the shortest remaining wait."""
        return min(blocked_requests, key=lambda blocked: blocked.wait_seconds)

    def _all_blocked_error(self) -> TimeoutError:
        """Return the public all-blocked routing error."""
        msg = "All routes are blocked by provider/key limits."
        return TimeoutError(msg)

    def _wait_for_blocked_request(
        self,
        *,
        request_id: str,
        blocked: _BlockedRequest,
    ) -> None:
        """Wait for one blocked sync route to become available."""
        self._log_limit_waiting(request_id=request_id, blocked=blocked)
        sleep(blocked.wait_seconds)

    async def _wait_for_blocked_request_async(
        self,
        *,
        request_id: str,
        blocked: _BlockedRequest,
    ) -> None:
        """Wait for one blocked async route to become available."""
        self._log_limit_waiting(request_id=request_id, blocked=blocked)
        await asyncio.sleep(blocked.wait_seconds)

    def _blocked_traces(
        self,
        blocked_requests: Sequence[_BlockedRequest],
    ) -> list[RoutingAttempt]:
        """Return skip traces for blocked routes skipped in favor of a fallback."""
        return [
            build_attempt_trace(
                route=blocked.request.route,
                settings=blocked.request.settings,
                key_id=blocked.request.key.key_id,
                wait_seconds=blocked.wait_seconds,
                error=RouteBlockedError("Route is blocked by provider/key limits."),
            )
            for blocked in blocked_requests
        ]

    def _trace_error(
        self,
        *,
        route: ExpandedRoute,
        settings: EffectiveSettings,
        error: Exception,
    ) -> RoutingAttempt:
        """Build a trace for an error before key resolution completed."""
        key_id = settings.key_id if isinstance(settings.key_id, int) else 0
        return build_attempt_trace(
            route=route,
            settings=settings,
            key_id=key_id,
            error=error,
        )

    def _complete_success(
        self,
        *,
        content: object,
        request_id: str,
        response: LLMRouterResponse,
        traces: Sequence[RoutingAttempt],
        final_trace: RoutingAttempt,
    ) -> LLMRouterResponse:
        """Attach routing traces, remember the session turn, and return success."""
        completed = response.model_copy(
            update={
                "routing_trace": [*traces, *response.routing_trace, final_trace],
            }
        )
        self._remember_success(content=content, response=completed)
        logger.info(
            "Router request completed",
            event_type="llm_router.router.request.completed",
            request_id=request_id,
            provider=completed.provider,
            model=completed.model,
        )
        return completed

    def _messages_for_content(self, content: object) -> tuple[ChatPart, ...]:
        """Build session-aware provider-neutral messages for one request."""
        if self.session is not None:
            return tuple(self.session.build_messages(content))
        if isinstance(content, str):
            return (content,)
        if isinstance(content, Sequence) and not isinstance(content, bytes | bytearray):
            return tuple(content)
        return (content,)

    def _log_request_started(self, *, request_id: str) -> None:
        """Log request start without payload content."""
        logger.info(
            "Router request started",
            event_type="llm_router.router.request.started",
            request_id=request_id,
        )

    def _log_routes_expanded(self) -> None:
        """Log the router construction route plan without payload content."""
        logger.info(
            "Routes expanded",
            event_type="llm_router.routing.routes.expanded",
            route_count=len(self.route_plan.routes),
        )

    def _log_request_failed(self, *, request_id: str, error: Exception) -> None:
        """Log terminal request failure without payload content."""
        logger.warning(
            "Router request failed",
            event_type="llm_router.router.request.failed",
            request_id=request_id,
            error_type=type(error).__name__,
            error_message=preview_exception_message(error),
        )

    def _log_route_selected(
        self,
        *,
        request_id: str,
        route: ExpandedRoute,
    ) -> None:
        """Log one route selection decision."""
        provider = (
            route.provider.value
            if isinstance(route.provider, Provider)
            else route.provider
        )
        logger.info(
            "Route selected",
            event_type="llm_router.routing.route.selected",
            request_id=request_id,
            provider=provider,
            model=route.model.value,
            route_index=route.route_index,
        )

    def _log_attempt_started(
        self,
        *,
        request_id: str,
        request: ResolvedRequest,
    ) -> None:
        """Log one provider-neutral route attempt start."""
        logger.info(
            "Route attempt started",
            event_type="llm_router.routing.attempt.started",
            request_id=request_id,
            provider=request.route.provider.value,
            model=request.route.model.value,
            route_index=request.route.route_index,
            key_id=request.key.key_id,
        )

    def _log_attempt_failed(
        self,
        *,
        request_id: str,
        route: ExpandedRoute,
        error: Exception,
    ) -> None:
        """Log one failed route attempt."""
        provider = (
            route.provider.value
            if isinstance(route.provider, Provider)
            else route.provider
        )
        event_type = (
            "llm_router.routing.attempt.timeout"
            if isinstance(error, TimeoutError)
            else "llm_router.routing.attempt.failed"
        )
        logger.warning(
            "Route attempt failed",
            event_type=event_type,
            request_id=request_id,
            provider=provider,
            model=route.model.value,
            route_index=route.route_index,
            error_type=type(error).__name__,
            error_message=preview_exception_message(error),
        )

    def _log_attempt_succeeded(
        self,
        *,
        request_id: str,
        request: ResolvedRequest,
    ) -> None:
        """Log one successful route attempt."""
        logger.info(
            "Route attempt succeeded",
            event_type="llm_router.routing.attempt.succeeded",
            request_id=request_id,
            provider=request.route.provider.value,
            model=request.route.model.value,
            route_index=request.route.route_index,
            key_id=request.key.key_id,
        )

    def _log_route_blocked(
        self,
        *,
        request_id: str,
        request: ResolvedRequest,
        wait_seconds: float,
    ) -> None:
        """Log one route skipped because it is currently blocked."""
        logger.info(
            "Route blocked",
            event_type="llm_router.routing.route.skipped",
            request_id=request_id,
            provider=request.route.provider.value,
            route_index=request.route.route_index,
            key_id=request.key.key_id,
            wait_seconds=wait_seconds,
        )

    def _log_limit_waiting(
        self,
        *,
        request_id: str,
        blocked: _BlockedRequest,
    ) -> None:
        """Log wait policy before sleeping for a blocked route."""
        logger.info(
            "Waiting for route limit",
            event_type="llm_router.routing.limit.waiting",
            request_id=request_id,
            provider=blocked.request.route.provider.value,
            route_index=blocked.request.route.route_index,
            key_id=blocked.request.key.key_id,
            wait_seconds=blocked.wait_seconds,
        )

    def _remember_success(self, *, content: object, response: object) -> None:
        """Persist successful responses to an attached session."""
        if self.session is None:
            return
        meta = {
            "provider": response.provider,
            "model": response.model,
            "usage": None if response.usage is None else response.usage.model_dump(),
            "routing_trace": [
                attempt.model_dump() for attempt in response.routing_trace
            ],
            "tool_trace": [step.model_dump() for step in response.tool_trace],
        }
        self.session.remember(
            user_content=content,
            assistant_text=response.output_text,
            assistant_meta=meta,
        )


def _pop_executor(kwargs: dict[str, object]) -> RouteExecutor | None:
    """Pop the private test/provider executor from constructor kwargs."""
    executor = kwargs.pop("_executor", None)
    if executor is None:
        return None
    return executor

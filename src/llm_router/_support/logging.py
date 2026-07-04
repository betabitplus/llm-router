"""Structured logging helpers for `llm_router`.

Why:
    Keeps library logging structured and library-safe while still offering
    lightweight configuration helpers for local runs, demos, and tests.

When to use:
    Import from here when `llm_router` code needs a logger, local logging
    setup, or shared retry logging callbacks.

How:
    Use `get_logger()` in library code.
    Use `configure_logging()` only in direct-run or application entrypoints.
"""

from __future__ import annotations

import functools
import inspect
import logging
import os
import time
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, ParamSpec, TypeVar, cast, overload

import structlog

from llm_router._support.error_formatting import preview_exception_message

if TYPE_CHECKING:
    import tenacity

P = ParamSpec("P")
R = TypeVar("R")


# ================================================================================
# Module Constants
# ================================================================================


_ENV_LEVEL = "LLM_ROUTER_LOG_LEVEL"
_ENV_JSON = "LLM_ROUTER_LOG_JSON"
_DEFAULT_LOCAL_LOG_LEVEL = "DEBUG"
_DEFAULT_THIRD_PARTY_LEVEL = logging.WARNING
_RETRY_SCHEDULED_EVENT_TYPE = "llm_router.provider.retry.scheduled"
_RETRY_EXHAUSTED_EVENT_TYPE = "llm_router.provider.retry.exhausted"

# Library best practice: prevent "No handler found" warnings for our namespace.
logging.getLogger("llm_router").addHandler(logging.NullHandler())


# ================================================================================
# Structlog Configuration Helpers
# ================================================================================


def _build_structlog_processors() -> list[Callable[..., Any]]:
    """Return the shared processor chain for stdlib-backed structlog logging."""
    return [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ]


def _configure_structlog_for_library() -> None:
    """Make structlog library-safe by default (no unconditional stdout prints).

    structlog's out-of-the-box defaults use a PrintLogger. For library code, it
    is better to route through stdlib logging and let the embedding app decide
    handlers and formatters.

    This function is intentionally conservative: if structlog is already
    configured by an application, do not override it.
    """
    cfg = structlog.get_config()
    if type(cfg.get("logger_factory")).__name__ != "PrintLoggerFactory":
        return

    structlog.configure(
        processors=_build_structlog_processors(),
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


_configure_structlog_for_library()


# ================================================================================
# Log Level Helpers
# ================================================================================


def _coerce_level(level: int | str | None) -> int:
    """Return a stdlib numeric log level from an int, str, or env default."""
    if level is None:
        level = os.getenv(_ENV_LEVEL, _DEFAULT_LOCAL_LOG_LEVEL)
    if isinstance(level, int):
        return level
    return logging.getLevelNamesMapping().get(str(level).upper(), logging.INFO)


def _resolve_optional_level(level: int | str) -> int | None:
    """Return a numeric log level or `None` when the input is invalid."""
    if isinstance(level, int):
        return level
    return logging.getLevelNamesMapping().get(level.upper())


# ================================================================================
# Public Logging Setup
# ================================================================================


def configure_logging(
    *,
    level: int | str | None = None,
    json: bool | None = None,
) -> None:
    """Configure structlog + stdlib logging for local runs.

    If the root logger already has handlers, this function does not replace
    them.
    """
    numeric_level = _coerce_level(level)
    want_json = json if json is not None else os.getenv(_ENV_JSON) == "1"

    root = logging.getLogger()
    if not root.handlers:
        formatter = structlog.stdlib.ProcessorFormatter(
            processor=_build_renderer(want_json=want_json),
            foreign_pre_chain=[
                structlog.stdlib.add_log_level,
                structlog.processors.TimeStamper(fmt="iso", utc=True),
            ],
        )
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        root.addHandler(handler)

    # Default to WARNING globally (avoid third-party noise), but explicitly
    # enable llm_router at DEBUG or the user-provided level.
    root.setLevel(_DEFAULT_THIRD_PARTY_LEVEL)

    structlog.configure(
        processors=_build_structlog_processors(),
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Intentionally do not add or replace handlers beyond installing a single
    # StreamHandler when no handlers exist, to keep this library-friendly.
    set_module_log_levels(_default_module_levels(numeric_level=numeric_level))


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a structlog logger for the given name.

    Note: this does not call `configure_logging()` automatically.
    """
    return structlog.get_logger(name)


# ================================================================================
# Operation Timing Helpers
# ================================================================================


class _OperationDurationLogger:
    """Context manager and decorator for operation duration logging."""

    def __init__(
        self,
        logger: structlog.stdlib.BoundLogger,
        *,
        event_type: str,
        message: str,
        level: int,
        fields: dict[str, object],
    ) -> None:
        """Store fixed logging metadata for one operation boundary."""
        self._logger = logger
        self._event_type = event_type
        self._message = message
        self._level = level
        self._fields = fields
        self._start: float | None = None

    def __enter__(self) -> None:
        """Start timing a synchronous code block."""
        self._start = time.perf_counter()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: object | None,
    ) -> bool:
        """Emit elapsed duration when a synchronous code block exits."""
        _ = exc_type, exc, traceback
        if self._start is not None:
            self._emit_duration(self._start)
        self._start = None
        return False

    @overload
    def __call__(
        self,
        func: Callable[P, Awaitable[R]],
    ) -> Callable[P, Awaitable[R]]: ...

    @overload
    def __call__(self, func: Callable[P, R]) -> Callable[P, R]: ...

    def __call__(
        self,
        func: Callable[P, R] | Callable[P, Awaitable[R]],
    ) -> Callable[P, R] | Callable[P, Awaitable[R]]:
        """Decorate a sync or async function with duration logging."""
        if inspect.iscoroutinefunction(func):
            async_func = cast("Callable[P, Awaitable[R]]", func)

            @functools.wraps(async_func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                """Execute an async operation and log elapsed duration."""
                start = time.perf_counter()
                try:
                    return await async_func(*args, **kwargs)
                finally:
                    self._emit_duration(start)

            return async_wrapper

        sync_func = cast("Callable[P, R]", func)

        @functools.wraps(sync_func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            """Execute a sync operation and log elapsed duration."""
            start = time.perf_counter()
            try:
                return sync_func(*args, **kwargs)
            finally:
                self._emit_duration(start)

        return sync_wrapper

    def _emit_duration(self, start: float) -> None:
        """Emit one structured duration event."""
        self._logger.log(
            self._level,
            self._message,
            event_type=self._event_type,
            duration_ms=int((time.perf_counter() - start) * 1000),
            **self._fields,
        )


def log_operation_duration(
    logger: structlog.stdlib.BoundLogger,
    *,
    event_type: str,
    message: str = "Operation completed",
    level: int = logging.DEBUG,
    **fields: object,
) -> _OperationDurationLogger:
    """Build a duration logger usable as a context manager or decorator."""
    return _OperationDurationLogger(
        logger,
        event_type=event_type,
        message=message,
        level=level,
        fields=fields,
    )


# ================================================================================
# Retry Event Helpers
# ================================================================================


def _extract_retry_timing(
    retry_state: tenacity.RetryCallState,
) -> tuple[float | None, int | None]:
    """Return Tenacity wait/max-attempt metadata from a retry state."""
    next_action = retry_state.next_action
    wait_seconds = None if next_action is None else float(next_action.sleep)
    stop = getattr(retry_state.retry_object, "stop", None)
    max_attempts = getattr(stop, "max_attempt_number", None)
    if not isinstance(max_attempts, int):
        max_attempts = None
    return wait_seconds, max_attempts


def _build_retry_scheduled_event(
    retry_state: tenacity.RetryCallState,
) -> dict[str, Any]:
    """Build the structured event payload for a scheduled retry."""
    outcome = retry_state.outcome
    exc = None if outcome is None else outcome.exception()
    wait_seconds, max_attempts = _extract_retry_timing(retry_state)
    event: dict[str, Any] = {
        "event_type": _RETRY_SCHEDULED_EVENT_TYPE,
        "attempt_number": int(retry_state.attempt_number),
    }
    if wait_seconds is not None:
        event["wait_seconds"] = wait_seconds
    if max_attempts is not None:
        event["max_attempts"] = max_attempts
    if exc is not None:
        event["error_type"] = type(exc).__name__
        event["error_message"] = preview_exception_message(exc)
    return event


def _build_retry_state_snapshot(
    scheduled_event: dict[str, Any],
) -> dict[str, Any]:
    """Return retry timing fields suitable for storing as request context."""
    snapshot = {"attempt_number": scheduled_event["attempt_number"]}
    for key in ("wait_seconds", "max_attempts"):
        value = scheduled_event.get(key)
        if value is not None:
            snapshot[key] = value
    return snapshot


def build_retry_before_sleep_logger(
    logger: structlog.stdlib.BoundLogger,
    *,
    context_getter: Callable[[], dict[str, Any]] | None = None,
    state_sink: Callable[[dict[str, Any]], None] | None = None,
) -> Callable[[tenacity.RetryCallState], None]:
    """Build a structured Tenacity `before_sleep` callback."""

    def _callback(retry_state: tenacity.RetryCallState) -> None:
        """Log one retry scheduling decision using the shared event schema."""
        event = _build_retry_scheduled_event(retry_state)
        if state_sink is not None:
            state_sink(_build_retry_state_snapshot(event))
        if context_getter is not None:
            event.update(context_getter())

        logger.warning("Provider retry scheduled", **event)

    return _callback


def log_retry_exhausted(
    logger: structlog.stdlib.BoundLogger,
    *,
    error: Exception,
    context: dict[str, Any] | None = None,
) -> None:
    """Emit a structured retry exhaustion event."""
    event: dict[str, Any] = {
        "event_type": _RETRY_EXHAUSTED_EVENT_TYPE,
        "error_type": type(error).__name__,
        "error_message": preview_exception_message(error),
    }
    if context:
        event.update(context)
    logger.warning("Provider retry exhausted", **event)


# ================================================================================
# Stdlib Logger Helpers
# ================================================================================


def set_module_log_levels(level_map: dict[str, int | str]) -> None:
    """Apply custom log levels to specific stdlib loggers."""
    for logger_name, level in level_map.items():
        numeric_level = _resolve_optional_level(level)
        if numeric_level is None:
            continue
        logging.getLogger(logger_name).setLevel(numeric_level)


# ================================================================================
# Internal Helpers
# ================================================================================


def _build_renderer(*, want_json: bool) -> Callable[..., Any]:
    """Return the renderer used by the optional default stream handler."""
    if want_json:
        return structlog.processors.JSONRenderer()
    return structlog.dev.ConsoleRenderer()


def _default_module_levels(*, numeric_level: int) -> dict[str, int]:
    """Return default per-module log levels for local logging setup."""
    return {
        # Our library: verbose by default for debuggable direct runs.
        "llm_router": numeric_level,
        # Common third-party libs: keep quiet.
        "httpx": _DEFAULT_THIRD_PARTY_LEVEL,
        "openai": _DEFAULT_THIRD_PARTY_LEVEL,
        "asyncio": _DEFAULT_THIRD_PARTY_LEVEL,
        "tenacity": _DEFAULT_THIRD_PARTY_LEVEL,
        "vcr": _DEFAULT_THIRD_PARTY_LEVEL,
        "urllib3": _DEFAULT_THIRD_PARTY_LEVEL,
    }

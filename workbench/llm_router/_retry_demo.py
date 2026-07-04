"""Shared retry-demo helpers for workbench provider scripts.

Why:
    Keeps the Tenacity setup, retry-event capture, and compact evidence shaping
    in one place so provider-specific retry demos stay focused on each
    provider's real retry contract.

When to use:
    Import from workbench retry scripts that wrap one live provider call in the
    same retry policy shape the adapter uses in `src/`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import tenacity


@dataclass(frozen=True, slots=True)
class RetryEvent:
    """One observed retry event captured by the Tenacity hook."""

    attempt_number: int
    exception_type: str
    message: str


def build_retry_params(
    *,
    retry: Any,  # noqa: ANN401
    events: list[RetryEvent],
    max_attempts: int = 3,
    min_wait_seconds: float = 1.0,
    max_wait_seconds: float = 8.0,
) -> dict[str, Any]:
    """Build one shared Tenacity config with event capture."""

    def _before_sleep(retry_state: tenacity.RetryCallState) -> None:
        """Capture one retry event before Tenacity sleeps."""
        exception = (
            None if retry_state.outcome is None else retry_state.outcome.exception()
        )
        if exception is None:
            return
        events.append(
            RetryEvent(
                attempt_number=int(retry_state.attempt_number),
                exception_type=type(exception).__name__,
                message=str(exception),
            )
        )

    return {
        "retry": retry,
        "wait": tenacity.wait_exponential(
            min=min_wait_seconds,
            max=max_wait_seconds,
        ),
        "stop": tenacity.stop_after_attempt(max_attempts),
        "before_sleep": _before_sleep,
        "reraise": True,
    }


def event_dicts(events: list[RetryEvent]) -> list[dict[str, Any]]:
    """Convert retry events into JSON-ready dictionaries."""
    return [
        {
            "attempt_number": event.attempt_number,
            "exception_type": event.exception_type,
            "message": event.message,
        }
        for event in events
    ]


def exception_type_names(exceptions: tuple[type[BaseException], ...]) -> list[str]:
    """Return stable exception type names for manual output."""
    return [exception.__name__ for exception in exceptions]

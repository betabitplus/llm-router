"""Internal ID helpers.

Why:
    Provides one private location for stable request, attempt, and tool-call
    identifiers used by runtime tracing.
"""

from __future__ import annotations

from itertools import count

_request_counter = count(1)


def next_request_id() -> str:
    """Return a stable process-local request identifier."""
    return f"req-{next(_request_counter)}"

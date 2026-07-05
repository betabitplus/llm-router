"""Private exception types and boundary helpers.

Why:
    Keeps internal failure categories separate from the public exception
    taxonomy until runtime boundaries translate them.
"""


class LLMRouterInternalError(Exception):
    """Base exception for private implementation failures."""


class RuntimeBoundaryUnavailableError(LLMRouterInternalError):
    """A later implementation phase owns the requested runtime behavior."""


class SessionSerializationError(LLMRouterInternalError):
    """Session persistence payload is invalid or cannot be written safely."""


class RouteBlockedError(LLMRouterInternalError):
    """One route is temporarily blocked by limiter state."""


class AllRoutesBlockedError(LLMRouterInternalError):
    """Every candidate route is temporarily blocked by limiter state."""


class KeyResolutionError(LLMRouterInternalError):
    """A concrete provider key could not be selected."""

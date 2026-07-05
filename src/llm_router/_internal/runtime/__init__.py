"""Runtime orchestration package.

Why:
    Owns provider-neutral routing, effective settings, limiter state, request
    envelopes, and tracing.

What belongs here:
    Router runtime orchestration and supporting private DTOs.

What does not belong here:
    Public facade signatures, provider SDK calls, or session serialization.
"""

from llm_router._internal.runtime.router import RouterRuntime as RouterRuntime

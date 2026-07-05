"""Provider-neutral runtime request DTOs.

Why:
    Keeps normalized request data separate from both public facade objects and
    concrete provider SDK payloads.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from llm_router._internal.contracts.models import ChatPart, LLMRouterResponse
from llm_router._internal.runtime.effective_settings import EffectiveSettings
from llm_router._internal.runtime.limiter import ResolvedKey
from llm_router._internal.runtime.routes import ExpandedRoute


@dataclass(frozen=True, slots=True)
class ResolvedRequest:
    """Provider-neutral request handed to an adapter or fake executor."""

    request_id: str
    route: ExpandedRoute
    settings: EffectiveSettings
    key: ResolvedKey
    messages: tuple[ChatPart, ...]
    content: object


class RouteExecutor(Protocol):
    """Protocol for provider-neutral execution ports."""

    def execute(self, request: ResolvedRequest) -> LLMRouterResponse:
        """Execute one synchronous request."""

    async def aexecute(self, request: ResolvedRequest) -> LLMRouterResponse:
        """Execute one asynchronous request."""

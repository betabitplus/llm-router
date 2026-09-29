# mutation-pin: REQ_ASYNC_PROVIDER_EXECUTION b5451a90524408d8
# pinned-by: claude-opus-5-5
from __future__ import annotations

from typing import Any

import pytest

from llm_router import LLMRouter, Model, Provider, RouterProfile

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.asyncio
@pytest.mark.verifies("REQ_ASYNC_PROVIDER_EXECUTION[revision==1]")
async def test_async_blocked_route_remembers_fallback_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_name = "NVIDIA_API_KEY"
    value = "mock-provider-auth-12345"
    monkeypatch.setenv(env_name, value)

    router = LLMRouter(
        [
            RouterProfile(model=Model.DEEPSEEK_V4_FLASH, provider=Provider.NVIDIA),
            RouterProfile(model=Model.LLAMA_8B, provider=Provider.NVIDIA),
        ]
    )
    runtime = getattr(router, "_runtime", router)

    query1_routes: list[Any] = []
    query2_routes: list[Any] = []
    active_query = 1

    orig_prepare = runtime._prepare_request

    def mock_prepare_request(
        request_id: Any,
        route: Any,
        settings: Any,
        content: Any,
    ) -> tuple[Any, float]:
        request, _ = orig_prepare(
            request_id=request_id,
            route=route,
            settings=settings,
            content=content,
        )
        if active_query == 1:
            query1_routes.append(route)
            if len(query1_routes) == 1:
                return request, 2.0
            return request, 0.0
        query2_routes.append(route)
        return request, 0.0

    monkeypatch.setattr(runtime, "_prepare_request", mock_prepare_request)

    async def mock_call_async(request: Any, timeout_seconds: Any) -> Any:
        assert request is not None
        assert timeout_seconds is not None
        return "mock-response-payload"

    monkeypatch.setattr(runtime, "_call_async_with_timeout", mock_call_async)

    def mock_complete_success(**kwargs: Any) -> str:
        assert kwargs
        return "sentinel-ok"

    monkeypatch.setattr(runtime, "_complete_success", mock_complete_success)

    fallback_flags: list[bool] = []
    orig_remember = runtime._remember_fallback_success

    def spy_remember(*args: Any, **kwargs: Any) -> Any:
        occurred = kwargs.get("fallback_occurred")
        fallback_flags.append(bool(occurred))
        return orig_remember(*args, **kwargs)

    monkeypatch.setattr(runtime, "_remember_fallback_success", spy_remember)

    result1 = await router.aquery("first prompt")
    assert result1 == "sentinel-ok"
    assert next(iter(fallback_flags)) is True
    assert runtime._sticky_start_route_index is not None

    active_query = 2
    result2 = await router.aquery("second prompt")
    assert result2 == "sentinel-ok"

    first_fallback_route = query1_routes[-1]
    second_query_first_route = next(iter(query2_routes))
    assert second_query_first_route is first_fallback_route

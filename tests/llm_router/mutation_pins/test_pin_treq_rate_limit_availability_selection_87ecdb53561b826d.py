# mutation-pin: TREQ_RATE_LIMIT_AVAILABILITY_SELECTION 87ecdb53561b826d
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router._api.types import Model, Provider, RouterProfile
from llm_router._internal.runtime.router import RouterRuntime

pytestmark = pytest.mark.verification_kind("unit")


class _FakeLimiter:
    def __init__(self, waits: dict[int, float]) -> None:
        self.waits = waits

    def wait_seconds(self, *, provider: Provider, key_id: int) -> float:
        assert provider is Provider.OPENROUTER
        return self.waits[key_id]


@pytest.mark.verifies("TREQ_RATE_LIMIT_AVAILABILITY_SELECTION[revision==1]")
def test_auto_key_with_all_blocked_picks_shortest_wait(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "openrouter-key-1")
    monkeypatch.setenv("OPENROUTER_API_KEY_2", "openrouter-key-2")
    runtime = RouterRuntime(
        spec=[
            RouterProfile(
                provider=Provider.OPENROUTER,
                model=Model.DEEPSEEK_V3,
                key_id="auto",
            )
        ],
    )
    runtime._limiter = _FakeLimiter({1: 9.0, 2: 3.0})
    first = runtime._settings_for_first_route(call_overrides={})
    route = next(iter(runtime._next_attempt_order(settings=first)))
    settings = runtime._settings_for_route(route=route, call_overrides={})
    request, wait_seconds = runtime._prepare_request(
        request_id="req-1",
        route=route,
        settings=settings,
        content="hello",
    )
    assert request.key.key_id == 2
    assert wait_seconds == 3.0

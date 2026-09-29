# mutation-pin: TREQ_RATE_LIMIT_AVAILABILITY_SELECTION 0c99e43a9ccfd476
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router import Model, Provider, RouterProfile
from llm_router._internal.runtime.router import RouterRuntime

pytestmark = pytest.mark.verification_kind("unit")


class _FakeLimiter:
    def __init__(self) -> None:
        self.waits: dict[int, float] = {}

    def wait_seconds(self, *, provider: Provider, key_id: int) -> float:
        assert provider is Provider.OPENROUTER
        return self.waits[key_id]


@pytest.mark.verifies("TREQ_RATE_LIMIT_AVAILABILITY_SELECTION[revision==1]")
def test_all_blocked_auto_key_picks_shortest_remaining_wait(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "openrouter-value-1")
    monkeypatch.setenv("OPENROUTER_API_KEY_2", "openrouter-value-2")
    runtime = RouterRuntime(
        spec=RouterProfile(
            provider=Provider.OPENROUTER,
            model=Model.DEEPSEEK_V3,
            key_id="auto",
            wait_for_cooldown_if_all_blocked=True,
        ),
    )
    limiter = _FakeLimiter()
    runtime._limiter = limiter
    first_settings = runtime._settings_for_first_route(call_overrides={})
    route = next(iter(runtime._next_attempt_order(settings=first_settings)))
    settings = runtime._settings_for_route(route=route, call_overrides={})
    scenarios = [
        ({1: 5.0, 2: 1.0}, 2),
        ({1: 1.0, 2: 5.0}, 1),
        ({1: 5.0, 2: 1.0}, 2),
        ({1: 4.0, 2: 0.5}, 2),
    ]
    for index, (waits, expected_key) in enumerate(scenarios):
        limiter.waits = waits
        request, wait_seconds = runtime._prepare_request(
            request_id=f"req-{index}",
            route=route,
            settings=settings,
            content="hello",
        )
        assert request.key.key_id == expected_key
        assert wait_seconds == waits[expected_key]

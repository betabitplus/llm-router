# mutation-pin: TREQ_RATE_LIMIT_AVAILABILITY_SELECTION e92263fea0939fa2
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import pytest

from llm_router import Model, Provider, ProviderLimits, RouterProfile
from llm_router._internal.runtime.router import RouterRuntime

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_RATE_LIMIT_AVAILABILITY_SELECTION[revision==1]")
def test_explicit_blocked_key_is_kept_without_candidate_probing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "openrouter-value-1")
    monkeypatch.setenv("OPENROUTER_API_KEY_2", "openrouter-value-2")
    runtime = RouterRuntime(
        spec=[
            RouterProfile(
                provider=Provider.OPENROUTER,
                model=Model.DEEPSEEK_V3,
                key_id=1,
            ),
        ],
        round_robin_start=False,
        shuffle_fallbacks=False,
    )
    limits = ProviderLimits(
        rps=0.2,
        rpm=1_000_000.0,
        cooldown_seconds=0.0,
        cooldown_after_failures=0,
    )
    runtime._limiter.record_success(
        provider=Provider.OPENROUTER, key_id=1, limits=limits
    )
    calls: list[object] = []
    real_candidates = runtime._keys.candidates

    def spy(**kwargs: object) -> object:
        calls.append(kwargs)
        return real_candidates(**kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(runtime._keys, "candidates", spy)
    settings = runtime._settings_for_first_route(call_overrides={})
    route = next(iter(runtime._next_attempt_order(settings=settings)))
    route_settings = runtime._settings_for_route(route=route, call_overrides={})
    request, wait_seconds = runtime._prepare_request(
        request_id="req-1",
        route=route,
        settings=route_settings,
        content="second",
    )
    assert request.key.key_id == 1
    assert wait_seconds > 0
    assert calls == []

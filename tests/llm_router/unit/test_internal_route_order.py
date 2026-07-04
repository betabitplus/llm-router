from __future__ import annotations

from llm_router import Model, Provider
from llm_router._internal.runtime.routes import (
    ExpandedRoute,
    RouteGenerationDefaults,
    RouteOrderOptions,
    RoutePlan,
    ordered_routes,
)


class ReverseShuffler:
    def __init__(self) -> None:
        self.calls = 0

    def shuffle(self, routes: list[ExpandedRoute]) -> None:
        self.calls += 1
        routes.reverse()


def _route(index: int, provider: Provider) -> ExpandedRoute:
    return ExpandedRoute(
        route_index=index,
        model=Model.GEMINI_FLASH,
        provider=provider,
        provider_model=f"provider-model-{index}",
        defaults=RouteGenerationDefaults(key_id=1),
    )


def _plan() -> RoutePlan:
    return RoutePlan(
        routes=(
            _route(0, Provider.AISTUDIO),
            _route(1, Provider.GOOGLE),
            _route(2, Provider.GEMINI_WEBAPI),
        )
    )


def test_round_robin_start_rotates_attempt_order_without_reindexing() -> None:
    routes = ordered_routes(
        _plan(),
        options=RouteOrderOptions(
            round_robin_start=True,
            shuffle_fallbacks=False,
            min_routes_for_fallback_shuffle=3,
            request_index=1,
            max_attempts=None,
        ),
    )

    assert [route.route_index for route in routes] == [1, 2, 0]


def test_shuffle_keeps_start_route_stable_and_shuffles_fallbacks() -> None:
    shuffler = ReverseShuffler()

    routes = ordered_routes(
        _plan(),
        options=RouteOrderOptions(
            round_robin_start=True,
            shuffle_fallbacks=True,
            min_routes_for_fallback_shuffle=3,
            request_index=1,
            max_attempts=None,
            shuffler=shuffler,
        ),
    )

    assert shuffler.calls == 1
    assert [route.route_index for route in routes] == [1, 0, 2]


def test_shuffle_respects_minimum_route_count() -> None:
    shuffler = ReverseShuffler()

    routes = ordered_routes(
        RoutePlan(routes=(_route(0, Provider.NVIDIA), _route(1, Provider.GROQ))),
        options=RouteOrderOptions(
            round_robin_start=False,
            shuffle_fallbacks=True,
            min_routes_for_fallback_shuffle=3,
            request_index=0,
            max_attempts=None,
            shuffler=shuffler,
        ),
    )

    assert shuffler.calls == 0
    assert [route.route_index for route in routes] == [0, 1]


def test_max_attempts_truncates_route_attempts_after_ordering() -> None:
    routes = ordered_routes(
        _plan(),
        options=RouteOrderOptions(
            round_robin_start=True,
            shuffle_fallbacks=False,
            min_routes_for_fallback_shuffle=3,
            request_index=2,
            max_attempts=2,
        ),
    )

    assert [route.route_index for route in routes] == [2, 0]

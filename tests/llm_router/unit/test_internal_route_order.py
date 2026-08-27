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
    def shuffle(self, routes: list[ExpandedRoute]) -> None:
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


def test_round_robin_rotates_attempt_order_without_reindexing() -> None:
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


def test_fallback_shuffle_keeps_selected_start_route_stable() -> None:
    routes = ordered_routes(
        _plan(),
        options=RouteOrderOptions(
            round_robin_start=True,
            shuffle_fallbacks=True,
            min_routes_for_fallback_shuffle=3,
            request_index=1,
            max_attempts=None,
            shuffler=ReverseShuffler(),
        ),
    )

    assert [route.route_index for route in routes] == [1, 0, 2]

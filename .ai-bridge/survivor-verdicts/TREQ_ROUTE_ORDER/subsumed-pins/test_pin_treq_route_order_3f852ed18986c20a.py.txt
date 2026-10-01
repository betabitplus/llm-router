# mutation-pin: TREQ_ROUTE_ORDER 3f852ed18986c20a
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router import Model, Provider
from llm_router._internal.runtime.routes import (
    ExpandedRoute,
    RouteGenerationDefaults,
    RouteOrderOptions,
    RoutePlan,
    ordered_routes,
)

pytestmark = pytest.mark.verification_kind("unit")


class ReverseShuffler:
    def shuffle(self, routes: list[ExpandedRoute]) -> None:
        routes.reverse()


def _route(index: int, provider_model: str) -> ExpandedRoute:
    return ExpandedRoute(
        route_index=index,
        model=Model.GEMINI_FLASH,
        provider=Provider.GOOGLE,
        provider_model=provider_model,
        defaults=RouteGenerationDefaults(key_id=1),
    )


def _plan() -> RoutePlan:
    return RoutePlan(
        routes=(
            _route(1, "a"),
            _route(2, "b"),
            _route(3, "c"),
            _route(4, "d"),
        )
    )


@pytest.mark.verifies("TREQ_ROUTE_ORDER[revision==1]")
def test_shuffle_disabled_keeps_fallback_order_and_cap() -> None:
    routes = ordered_routes(
        _plan(),
        options=RouteOrderOptions(
            round_robin_start=False,
            shuffle_fallbacks=False,
            min_routes_for_fallback_shuffle=2,
            request_index=0,
            max_attempts=3,
            shuffler=ReverseShuffler(),
        ),
    )

    assert [route.route_index for route in routes] == [1, 2, 3]

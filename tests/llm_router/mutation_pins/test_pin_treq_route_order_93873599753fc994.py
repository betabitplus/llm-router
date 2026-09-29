# mutation-pin: TREQ_ROUTE_ORDER 93873599753fc994
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


def _route(index: int, provider: Provider) -> ExpandedRoute:
    return ExpandedRoute(
        route_index=index,
        model=Model.GEMINI_FLASH,
        provider=provider,
        provider_model=f"provider-model-{index}",
        defaults=RouteGenerationDefaults(key_id=1),
    )


@pytest.mark.verifies("TREQ_ROUTE_ORDER[revision==1]")
def test_fallback_shuffle_on_tuple_plan_keeps_start_first() -> None:
    plan = RoutePlan(
        routes=(
            _route(0, Provider.AISTUDIO),
            _route(1, Provider.GOOGLE),
            _route(2, Provider.GEMINI_WEBAPI),
        )
    )
    routes = ordered_routes(
        plan,
        options=RouteOrderOptions(
            round_robin_start=False,
            shuffle_fallbacks=True,
            min_routes_for_fallback_shuffle=2,
            request_index=0,
            max_attempts=None,
            shuffler=ReverseShuffler(),
        ),
    )

    assert [route.route_index for route in routes] == [0, 2, 1]

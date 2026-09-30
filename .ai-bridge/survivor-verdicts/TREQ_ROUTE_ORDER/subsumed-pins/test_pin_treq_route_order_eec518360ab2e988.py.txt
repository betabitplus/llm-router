# mutation-pin: TREQ_ROUTE_ORDER eec518360ab2e988
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


def _route(index: int, provider: Provider) -> ExpandedRoute:
    return ExpandedRoute(
        route_index=index,
        model=Model.GEMINI_FLASH,
        provider=provider,
        provider_model=f"provider-model-{index}",
        defaults=RouteGenerationDefaults(key_id=1),
    )


@pytest.mark.verifies("TREQ_ROUTE_ORDER[revision==1]")
def test_default_shuffler_keeps_start_first_and_all_routes() -> None:
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
            round_robin_start=True,
            shuffle_fallbacks=True,
            min_routes_for_fallback_shuffle=2,
            request_index=1,
            max_attempts=None,
            shuffler=None,
        ),
    )

    assert routes[0].route_index == 1
    assert sorted(route.route_index for route in routes) == [0, 1, 2]

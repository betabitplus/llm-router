# mutation-pin: TREQ_ROUTE_ORDER 7f06d09ceb421dcd
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router._internal.runtime.routes import (
    RouteOrderOptions,
    RoutePlan,
    ordered_routes,
)

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_ROUTE_ORDER[revision==1]")
def test_empty_plan_yields_empty_tuple() -> None:
    routes = ordered_routes(
        RoutePlan(routes=()),
        options=RouteOrderOptions(
            round_robin_start=True,
            shuffle_fallbacks=True,
            min_routes_for_fallback_shuffle=2,
            request_index=3,
            max_attempts=2,
        ),
    )

    assert routes == ()
    assert isinstance(routes, tuple)

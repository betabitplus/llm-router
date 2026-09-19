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


def _plan() -> RoutePlan:
    return RoutePlan(
        routes=(
            _route(0, Provider.AISTUDIO),
            _route(1, Provider.GOOGLE),
            _route(2, Provider.GEMINI_WEBAPI),
        )
    )


@pytest.mark.verifies("TREQ_ROUTE_ORDER[revision==1]")
@pytest.mark.coverage_item("VC_ROUTE_ORDER_ROUND_ROBIN_IDENTITY")
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


@pytest.mark.verifies("TREQ_ROUTE_ORDER[revision==1]")
@pytest.mark.coverage_item("VC_ROUTE_ORDER_SHUFFLE_START_IDENTITY")
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


@pytest.mark.verifies("TREQ_ROUTE_ORDER[revision==1]")
@pytest.mark.coverage_item("VC_ROUTE_ORDER_STICKY_START_IDENTITY")
def test_explicit_successful_start_survives_shuffle_and_attempt_cap() -> None:
    routes = ordered_routes(
        _plan(),
        options=RouteOrderOptions(
            round_robin_start=True,
            shuffle_fallbacks=True,
            min_routes_for_fallback_shuffle=3,
            request_index=1,
            max_attempts=2,
            selected_start_route_index=2,
            shuffler=ReverseShuffler(),
        ),
    )

    assert [route.route_index for route in routes] == [2, 1]


@pytest.mark.verifies("REQ_ROUTE_ATTEMPT_LIMIT[revision==1]")
@pytest.mark.coverage_item("VC_ROUTE_ATTEMPT_LIMIT_BOUNDARIES")
@pytest.mark.coverage_path("minimum-cap")
def test_attempt_limit_minimum_keeps_only_one_candidate() -> None:
    routes = ordered_routes(
        _plan(),
        options=RouteOrderOptions(
            round_robin_start=False,
            shuffle_fallbacks=False,
            min_routes_for_fallback_shuffle=3,
            request_index=0,
            max_attempts=1,
        ),
    )

    assert [route.route_index for route in routes] == [0]


@pytest.mark.verifies("REQ_ROUTE_ATTEMPT_LIMIT[revision==1]")
@pytest.mark.coverage_item("VC_ROUTE_ATTEMPT_LIMIT_BOUNDARIES")
@pytest.mark.coverage_path("intermediate-cap")
def test_attempt_limit_truncates_larger_candidate_set_exactly() -> None:
    routes = ordered_routes(
        _plan(),
        options=RouteOrderOptions(
            round_robin_start=False,
            shuffle_fallbacks=False,
            min_routes_for_fallback_shuffle=3,
            request_index=0,
            max_attempts=2,
        ),
    )

    assert [route.route_index for route in routes] == [0, 1]

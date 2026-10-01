# mutation-pin: TREQ_ROUTE_ORDER FN-69242EB7
# pinned-by: delegate, one pin for 4 pins of ordered_routes
# kills: 3f852ed18986c20a 73f9e013ae38b43a 7f06d09ceb421dcd 93873599753fc994
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


def _route(index: int) -> ExpandedRoute:
    return ExpandedRoute(
        route_index=index,
        model=Model.GEMINI_FLASH,
        provider=Provider.GOOGLE,
        provider_model=f"provider-model-{index}",
        defaults=RouteGenerationDefaults(key_id=1),
    )


def _plan() -> RoutePlan:
    return RoutePlan(routes=(_route(0), _route(1), _route(2), _route(3)))


def _options(
    shuffle: bool,
    shuffler: ReverseShuffler | None,
    max_attempts: int | None = None,
    round_robin: bool = False,
    request_index: int = 0,
) -> RouteOrderOptions:
    return RouteOrderOptions(
        round_robin_start=round_robin,
        shuffle_fallbacks=shuffle,
        min_routes_for_fallback_shuffle=2,
        request_index=request_index,
        max_attempts=max_attempts,
        shuffler=shuffler,
    )


@pytest.mark.verifies("TREQ_ROUTE_ORDER[revision==1]")
def test_route_ordering() -> None:
    empty = ordered_routes(RoutePlan(routes=()), options=_options(True, None))
    assert empty == ()
    assert isinstance(empty, tuple)

    plain = ordered_routes(
        _plan(), options=_options(False, ReverseShuffler(), max_attempts=3)
    )
    assert [r.route_index for r in plain] == [0, 1, 2]

    shuffled = ordered_routes(_plan(), options=_options(True, ReverseShuffler()))
    assert [r.route_index for r in shuffled] == [0, 3, 2, 1]

    default = ordered_routes(_plan(), options=_options(True, None))
    assert next(iter(default)).route_index == 0
    assert sorted(r.route_index for r in default) == [0, 1, 2, 3]

    rotated = ordered_routes(
        _plan(), options=_options(True, None, round_robin=True, request_index=2)
    )
    assert next(iter(rotated)).route_index == 2
    assert sorted(r.route_index for r in rotated) == [0, 1, 2, 3]

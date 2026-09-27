# mutation-pin: REQ_REQUEST_OVERRIDE_PRECEDENCE bf8a96501e88d45d
# pinned-by: claude-opus-5-5: The mutant drops the step that merges request-level provider kwargs into the effective kwargs. As a result, a call override such as custom_kwarg is silently lost (the effective kwargs come out as {} instead of {'custom_kwarg': 'value'}). This breaks the requirement that request-level settings overri
from __future__ import annotations

import pytest

from llm_router._internal.config import build_default_config
from llm_router._internal.runtime.effective_settings import (
    RouterDefaults,
    resolve_effective_settings,
)
from llm_router._internal.runtime.routes import RouteGenerationDefaults

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_REQUEST_OVERRIDE_PRECEDENCE[revision==1]")
def test_request_provider_kwargs_override_defaults_and_preserve_unrelated() -> None:
    config = build_default_config()
    route_defaults = RouteGenerationDefaults(
        key_id=0,
        kwargs={
            "unrelated_route_kwarg": "route_default_value",
            "clashing_route_kwarg": "route_initial_value",
        },
    )
    router_defaults = RouterDefaults(
        values={},
        kwargs={
            "unrelated_router_kwarg": "router_default_value",
            "clashing_router_kwarg": "router_initial_value",
        },
    )
    call_overrides = {
        "custom_provider_kwarg": "request_custom_value",
        "clashing_route_kwarg": "request_override_route",
        "clashing_router_kwarg": "request_override_router",
    }

    settings = resolve_effective_settings(
        config=config,
        route_defaults=route_defaults,
        route_policy_defaults={},
        router_defaults=router_defaults,
        call_overrides=call_overrides,
    )

    assert settings.kwargs == {
        "unrelated_route_kwarg": "route_default_value",
        "clashing_route_kwarg": "request_override_route",
        "unrelated_router_kwarg": "router_default_value",
        "clashing_router_kwarg": "request_override_router",
        "custom_provider_kwarg": "request_custom_value",
    }

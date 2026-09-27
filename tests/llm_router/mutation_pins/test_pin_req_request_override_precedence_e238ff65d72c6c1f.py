# mutation-pin: REQ_REQUEST_OVERRIDE_PRECEDENCE e238ff65d72c6c1f
# pinned-by: claude-opus-5-5: The mutant never merges router-level provider kwargs into the effective kwargs, so router defaults are silently lost. The confirmed input shows this: with no request override, {'custom_kwarg': 'test_val'} disappears. That breaks the precedence chain (route < router < request) and the criterion that
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
def test_router_default_kwargs_override_route_and_yield_to_request() -> None:
    config = build_default_config()
    route_defaults = RouteGenerationDefaults(
        key_id=1,
        kwargs={
            "priority_lane": "standard",
            "tenant_id": "tenant-route",
            "log_tag": "audit-route",
        },
    )
    router_defaults = RouterDefaults(
        values={},
        kwargs={
            "priority_lane": "expedited",
            "tenant_id": "tenant-router",
            "routing_tag": "cluster-primary",
        },
    )
    call_overrides = {
        "tenant_id": "tenant-call",
        "client_label": "batch-worker",
    }

    effective = resolve_effective_settings(
        config=config,
        route_defaults=route_defaults,
        route_policy_defaults={},
        router_defaults=router_defaults,
        call_overrides=call_overrides,
    )

    assert effective.kwargs["priority_lane"] == "expedited"
    assert effective.kwargs["tenant_id"] == "tenant-call"
    assert effective.kwargs["routing_tag"] == "cluster-primary"
    assert effective.kwargs["log_tag"] == "audit-route"
    assert effective.kwargs["client_label"] == "batch-worker"
    assert effective.kwargs == {
        "priority_lane": "expedited",
        "tenant_id": "tenant-call",
        "routing_tag": "cluster-primary",
        "log_tag": "audit-route",
        "client_label": "batch-worker",
    }

# semantic-mutant: SM-4D75202A
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
def test_falsy_call_provider_kwargs_override_inherited_kwargs() -> None:
    config = build_default_config()
    route_defaults = RouteGenerationDefaults(
        key_id=0,
        kwargs={"top_k": 40, "stop": ["x"], "unrelated": "kept"},
    )
    router_defaults = RouterDefaults(kwargs={"n": 3, "flag": True})

    omitted = resolve_effective_settings(
        config=config,
        route_defaults=route_defaults,
        route_policy_defaults={},
        router_defaults=router_defaults,
        call_overrides={},
    )
    assert omitted.kwargs["top_k"] == 40
    assert omitted.kwargs["n"] == 3

    explicit = resolve_effective_settings(
        config=config,
        route_defaults=route_defaults,
        route_policy_defaults={},
        router_defaults=router_defaults,
        call_overrides={
            "top_k": 0,
            "stop": [],
            "n": None,
            "flag": False,
            "custom_kwarg": 0,
        },
    )
    assert explicit.kwargs["top_k"] == 0
    assert explicit.kwargs["stop"] == []
    assert explicit.kwargs["n"] is None
    assert explicit.kwargs["flag"] is False
    assert explicit.kwargs["custom_kwarg"] == 0
    assert explicit.kwargs["unrelated"] == "kept"

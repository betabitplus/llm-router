# mutation-pin: TREQ_CONFIG_MODEL_DECLARATION SM-8D7935BF
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import dataclasses

import pytest

from llm_router._api.errors import ConfigurationError
from llm_router._api.types import Model, RouterProfile
from llm_router._internal.config import build_default_config
from llm_router._internal.runtime.routes import expand_route_plan

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_CONFIG_MODEL_DECLARATION[revision==1]")
def test_undeclared_string_model_is_rejected_when_expanding_routes() -> None:
    base = build_default_config()
    declared = base.default_model
    undeclared = next(iter(m for m in Model if m != declared))
    catalog = dataclasses.replace(
        base.catalog,
        models={declared: base.models[declared]},
    )
    config = dataclasses.replace(base, catalog=catalog)
    assert undeclared not in config.models

    declared_profile = RouterProfile(model=declared.value, provider="custom-route")
    plan = expand_route_plan(declared_profile, config=config)
    assert {route.model for route in plan.routes} == {declared}

    undeclared_profile = RouterProfile(
        model=undeclared.value,
        provider="custom-route",
    )
    with pytest.raises(ConfigurationError, match=r"Unknown model"):
        expand_route_plan(undeclared_profile, config=config)
    with pytest.raises(ConfigurationError, match=r"Unknown model"):
        expand_route_plan(undeclared.value, config=config)

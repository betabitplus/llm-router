# mutation-pin: TREQ_CONFIG_MODEL_DECLARATION e1379ec0c0ed9e96
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import pytest

from llm_router._api.types import Model
from llm_router._internal.config import build_default_config
from llm_router._internal.runtime.routes import expand_route_plan

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_CONFIG_MODEL_DECLARATION[revision==1]")
def test_expand_route_plan_maps_declared_string_to_model_member() -> None:
    config = build_default_config()
    declared = next(iter(config.models))

    plan = expand_route_plan(declared.value, config=config)

    assert plan.routes
    for route in plan.routes:
        assert isinstance(route.model, Model)
        assert route.model is declared

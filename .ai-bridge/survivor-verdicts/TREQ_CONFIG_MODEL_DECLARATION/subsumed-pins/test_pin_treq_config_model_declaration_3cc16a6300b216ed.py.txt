# mutation-pin: TREQ_CONFIG_MODEL_DECLARATION 3cc16a6300b216ed
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import pytest

from llm_router._internal.config import build_default_config
from llm_router._internal.runtime.routes import expand_route_plan

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_CONFIG_MODEL_DECLARATION[revision==1]")
def test_declared_model_reaches_routes_for_enum_and_str() -> None:
    config = build_default_config()
    model = config.default_model

    from_enum = expand_route_plan(model, config=config)
    from_str = expand_route_plan(model.value, config=config)

    assert from_enum.routes
    assert from_str.routes
    assert {route.model for route in from_enum.routes} == {model}
    assert {route.model for route in from_str.routes} == {model}

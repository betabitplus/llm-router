# mutation-pin: TREQ_CONFIG_MODEL_DECLARATION 5ed9365a38636da5
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import pytest

from llm_router._api.errors import ConfigurationError
from llm_router._internal.config import build_default_config
from llm_router._internal.runtime.routes import expand_route_plan

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_CONFIG_MODEL_DECLARATION[revision==1]")
def test_route_plan_rejects_unknown_model_string() -> None:
    config = build_default_config()

    with pytest.raises(ConfigurationError, match=r"^Unknown model: no-such-model$"):
        expand_route_plan("no-such-model", config=config)

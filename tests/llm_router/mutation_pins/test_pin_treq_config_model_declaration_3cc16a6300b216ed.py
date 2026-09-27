# mutation-pin: TREQ_CONFIG_MODEL_DECLARATION 3cc16a6300b216ed
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router._internal.config import build_default_config
from llm_router._internal.runtime.routes import _resolve_model

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_CONFIG_MODEL_DECLARATION[revision==1]")
def test_resolve_model_returns_declared_model_for_enum_and_str() -> None:
    config = build_default_config()
    model = config.default_model

    assert _resolve_model(model, config=config) == model
    assert _resolve_model(model.value, config=config) == model

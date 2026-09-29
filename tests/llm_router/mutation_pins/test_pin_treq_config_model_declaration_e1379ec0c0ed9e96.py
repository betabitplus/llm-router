# mutation-pin: TREQ_CONFIG_MODEL_DECLARATION e1379ec0c0ed9e96
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router._api.types import Model
from llm_router._internal.config import build_default_config
from llm_router._internal.runtime.routes import _resolve_model

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_CONFIG_MODEL_DECLARATION[revision==1]")
def test_resolve_model_converts_declared_string_to_enum_member() -> None:
    config = build_default_config()
    model = config.default_model
    value = model.value

    resolved = _resolve_model(value, config=config)

    assert isinstance(resolved, Model)
    assert resolved == model

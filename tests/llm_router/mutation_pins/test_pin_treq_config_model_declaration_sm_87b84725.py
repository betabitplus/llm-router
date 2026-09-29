# mutation-pin: TREQ_CONFIG_MODEL_DECLARATION SM-87B84725
# pinned-by: claude-opus-5-5 and gemini-3.1-pro-high
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import dataclasses

import pytest

from llm_router._api.types import Model
from llm_router._internal.config import build_default_config
from llm_router._internal.runtime.routes import _resolve_model

pytestmark = pytest.mark.verification_kind("unit")


class _EnumOnlyModels(dict):
    """Declared-model mapping that recognises only Model members as keys."""

    def __contains__(self, key: object) -> bool:
        return type(key) is Model and dict.__contains__(self, key)


@pytest.mark.verifies("TREQ_CONFIG_MODEL_DECLARATION[revision==1]")
def test_declared_model_string_is_accepted_via_resolved_enum() -> None:
    base = build_default_config()
    catalog = dataclasses.replace(base.catalog)
    object.__setattr__(catalog, "models", _EnumOnlyModels(base.catalog.models))
    config = dataclasses.replace(base, catalog=catalog)
    model = config.default_model

    assert model in config.models
    assert _resolve_model(model, config=config) == model
    assert _resolve_model(model.value, config=config) == model

# mutation-pin: TREQ_CONFIG_MODEL_DECLARATION SM-8D7935BF
# pinned-by: claude-opus-5-5
from __future__ import annotations

import dataclasses

import pytest

from llm_router._api.errors import ConfigurationError
from llm_router._api.types import Model
from llm_router._internal.config import build_default_config
from llm_router._internal.runtime.routes import _resolve_model

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_CONFIG_MODEL_DECLARATION[revision==1]")
def test_resolve_model_rejects_undeclared_string_model() -> None:
    base = build_default_config()
    declared = base.default_model
    undeclared = next(iter(m for m in Model if m != declared))
    catalog = dataclasses.replace(
        base.catalog,
        models={declared: base.models[declared]},
    )
    config = dataclasses.replace(base, catalog=catalog)

    assert _resolve_model(declared.value, config=config) == declared
    with pytest.raises(ConfigurationError, match=r"Unknown model"):
        _resolve_model(undeclared.value, config=config)
    with pytest.raises(ConfigurationError, match=r"Unknown model"):
        _resolve_model(undeclared, config=config)

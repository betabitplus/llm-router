# mutation-pin: TREQ_CONFIG_MODEL_DECLARATION 5ed9365a38636da5
# pinned-by: claude-opus-5-5
from __future__ import annotations

import re

import pytest

from llm_router import ConfigurationError
from llm_router._internal.config import build_default_config
from llm_router._internal.runtime.routes import _resolve_model

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_CONFIG_MODEL_DECLARATION[revision==1]")
def test_resolve_model_raises_configuration_error_for_unknown_model_string() -> None:
    config = build_default_config()
    unknown_model = "no-such-model"

    with pytest.raises(
        ConfigurationError,
        match=re.escape(f"Unknown model: {unknown_model}"),
    ):
        _resolve_model(unknown_model, config=config)

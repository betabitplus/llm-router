# semantic-mutant: SM-70BDADCC
from __future__ import annotations

from dataclasses import replace

import pytest

from llm_router._api.errors import ConfigurationError
from llm_router._api.types import Provider
from llm_router._internal.config import build_default_config, validate_config

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_INVALID_CONFIGURATION_ERRORS[revision==2]")
def test_later_model_mapping_with_unknown_provider_is_rejected() -> None:
    config = build_default_config()
    missing = next(
        p for p in Provider if p != config.default_provider
    )
    providers = {
        p: spec for p, spec in config.catalog.providers.items() if p != missing
    }
    models = {
        config.default_model: {
            config.default_provider: "model-a",
            missing: "model-b",
        }
    }
    catalog = replace(config.catalog, providers=providers, models=models)
    broken = replace(config, catalog=catalog)

    with pytest.raises(ConfigurationError, match=r"unknown provider"):
        validate_config(broken)

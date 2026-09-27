# mutation-pin: REQ_CONFIG_INSTALLATION_COHERENCE a2e61f2155653e45
# pinned-by: claude-opus-5-5
from __future__ import annotations

from dataclasses import replace

import pytest

import llm_router as package
import llm_router._api.config as api_config

pytestmark = pytest.mark.verification_kind("unit")

ConfigurationError = getattr(
    package,
    "ConfigurationError",
    getattr(api_config, "ConfigurationError", None),
)


@pytest.mark.verifies("REQ_CONFIG_INSTALLATION_COHERENCE[revision==2]")
def test_install_config_rejects_catalog_missing_defaults() -> None:
    initial_config = package.get_config()

    invalid_catalog = replace(initial_config.catalog, providers={}, models={})
    invalid_config = replace(initial_config, catalog=invalid_catalog)

    assert invalid_config.default_provider not in invalid_config.catalog.providers
    assert invalid_config.default_model not in invalid_config.catalog.models

    with pytest.raises(ConfigurationError):
        package.install_config(invalid_config)

    assert package.get_config() is initial_config

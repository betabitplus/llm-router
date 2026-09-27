# mutation-pin: REQ_CONFIG_INSTALLATION_COHERENCE a2e61f2155653e45
# pinned-by: claude-opus-5-5: The mutant drops validate_config, so install_config accepts an incoherent snapshot (an empty catalog that lacks the default provider and model) and makes it active instead of raising ConfigurationError. This breaks the Feature's validation promise and the "coherent" installation this requirement ask
from __future__ import annotations

from dataclasses import fields, replace

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
def test_install_config_rejects_catalog_missing_defaults_and_preserves_active_config() -> None:
    initial_config = package.get_config()

    catalog_fields = {f.name for f in fields(initial_config.catalog)}
    catalog_replacements = {
        name: {}
        for name in ("providers", "provider_base_urls", "models")
        if name in catalog_fields
    }
    invalid_catalog = replace(initial_config.catalog, **catalog_replacements)
    invalid_config = replace(initial_config, catalog=invalid_catalog)

    assert invalid_config.default_provider not in invalid_config.catalog.providers
    assert invalid_config.default_model not in invalid_config.catalog.models

    with pytest.raises(ConfigurationError):
        package.install_config(invalid_config)

    assert package.get_config() is initial_config

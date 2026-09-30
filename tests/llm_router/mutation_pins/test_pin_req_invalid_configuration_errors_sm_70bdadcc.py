# mutation-pin: REQ_INVALID_CONFIGURATION_ERRORS SM-70BDADCC
# pinned-by: claude-opus-5-5
# written-by: claude-opus-5-5, the last resort, the verdict's own model with tools
from __future__ import annotations

import pytest

from llm_router import (
    ConfigurationError,
    LLMRouterConfig,
    Model,
    Provider,
    ProviderCatalog,
    get_config,
    install_config,
)

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_INVALID_CONFIGURATION_ERRORS[revision==2]")
def test_second_model_mapping_to_uncatalogued_provider_is_rejected() -> None:
    installed = get_config()
    catalogued = {
        provider: spec
        for provider, spec in installed.catalog.providers.items()
        if provider is not Provider.GOOGLE
    }
    # The first mapping is catalogued; only the later one is unknown.
    models = {
        Model.GEMINI_FLASH: {
            Provider.AISTUDIO: "gemini-3.6-flash",
            Provider.GOOGLE: "gemini-3.6-flash",
        },
    }
    catalog = ProviderCatalog(
        providers=catalogued,
        provider_base_urls=installed.provider_base_urls,
        models=models,
    )
    invalid = LLMRouterConfig(
        default_provider=Provider.AISTUDIO,
        default_model=Model.GEMINI_FLASH,
        default_key_id=installed.default_key_id,
        defaults=installed.defaults,
        catalog=catalog,
    )

    with pytest.raises(
        ConfigurationError,
        match=r"^model 'gemini-3\.6-flash' references an unknown provider\.$",
    ):
        install_config(invalid)

    assert get_config() is installed

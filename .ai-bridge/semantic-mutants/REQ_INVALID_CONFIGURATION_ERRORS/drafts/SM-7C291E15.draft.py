# semantic-mutant: SM-7C291E15
from __future__ import annotations

from dataclasses import replace

import pytest

from llm_router import ConfigurationError
from llm_router._api.types import Model, Provider
from llm_router._internal.config import build_default_config, validate_config

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_INVALID_CONFIGURATION_ERRORS[revision==2]")
def test_missing_base_url_for_non_default_provider_is_rejected() -> None:
    config = build_default_config()
    google_spec = config.catalog.providers[Provider.GOOGLE]
    catalog = replace(
        config.catalog,
        providers={Provider.GOOGLE: google_spec},
        provider_base_urls={},
        models={Model.GEMINI_FLASH: {Provider.GOOGLE: "gemini-flash"}},
    )
    invalid = replace(
        config,
        default_provider=Provider.GOOGLE,
        default_model=Model.GEMINI_FLASH,
        catalog=catalog,
    )

    with pytest.raises(ConfigurationError, match=r"base URL"):
        validate_config(invalid)

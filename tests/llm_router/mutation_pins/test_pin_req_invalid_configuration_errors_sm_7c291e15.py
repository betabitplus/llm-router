# mutation-pin: REQ_INVALID_CONFIGURATION_ERRORS SM-7C291E15
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

from dataclasses import replace

import pytest

import llm_router as package

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_INVALID_CONFIGURATION_ERRORS[revision==2]")
def test_missing_base_url_for_non_default_provider_is_rejected() -> None:
    current = package.get_config()
    kept = {
        provider: url
        for provider, url in current.catalog.provider_base_urls.items()
        if provider == current.default_provider
    }
    catalog = replace(current.catalog, provider_base_urls=kept)
    invalid = replace(current, catalog=catalog)

    with pytest.raises(package.ConfigurationError, match=r"requires a base URL"):
        package.install_config(invalid)

    assert package.get_config() is current

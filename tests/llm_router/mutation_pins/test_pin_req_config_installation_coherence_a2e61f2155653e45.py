# mutation-pin: REQ_CONFIG_INSTALLATION_COHERENCE a2e61f2155653e45
# pinned-by: claude-opus-5-5
from __future__ import annotations

from dataclasses import replace

import pytest

import llm_router as package

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_CONFIG_INSTALLATION_COHERENCE[revision==2]")
def test_install_config_rejects_catalog_missing_defaults() -> None:
    current = package.get_config()
    empty_catalog = replace(current.catalog, providers={}, models={})
    invalid_config = replace(current, catalog=empty_catalog)

    with pytest.raises(package.ConfigurationError, match=r".+"):
        package.install_config(invalid_config)

    assert package.get_config() is current

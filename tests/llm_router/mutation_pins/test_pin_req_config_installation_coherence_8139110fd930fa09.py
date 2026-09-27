# mutation-pin: REQ_CONFIG_INSTALLATION_COHERENCE 8139110fd930fa09
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

import llm_router as package

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_CONFIG_INSTALLATION_COHERENCE[revision==2]")
def test_install_config_with_non_config_raises_type_error() -> None:
    current = package.get_config()
    invalid_config = {"name": "stand_in"}

    with pytest.raises(TypeError):
        package.install_config(invalid_config)

    assert package.get_config() is current

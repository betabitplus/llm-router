"""Minimal public package smoke tests."""

from __future__ import annotations

from dataclasses import replace

import pytest

import llm_router as package
from llm_router import LLMRouterConfig


@pytest.mark.verifies("REQ_PUBLIC_API_SURFACE[revision==1]")
@pytest.mark.verification_kind("unit")
def test_declared_public_api_resolves() -> None:
    assert package.__version__
    assert all(hasattr(package, name) for name in package.__all__)


@pytest.mark.verifies("REQ_CONFIG_INSTALLATION_COHERENCE[revision==2]")
@pytest.mark.coverage_item("VC_CONFIG_INSTALLATION_ROUND_TRIP")
@pytest.mark.verification_kind("unit")
def test_public_config_lifecycle_round_trips_replacement_snapshot() -> None:
    config = package.get_config()
    replacement = replace(config, default_key_id=config.default_key_id + 1)

    assert isinstance(replacement, LLMRouterConfig)
    assert replacement is not config
    assert package.install_config(replacement) is replacement
    assert package.get_config() is replacement

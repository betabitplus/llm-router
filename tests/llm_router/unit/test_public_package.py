"""Minimal public package smoke tests."""

from __future__ import annotations

import pytest

import llm_router as package
from llm_router import LLMRouterConfig


@pytest.mark.verifies("REQ_PUBLIC_API_SURFACE[revision==1]")
@pytest.mark.verification_kind("unit")
def test_declared_public_api_resolves() -> None:
    assert package.__version__
    assert all(hasattr(package, name) for name in package.__all__)


@pytest.mark.verifies("REQ_CONFIG_INSTALLATION_COHERENCE[revision==1]")
@pytest.mark.verification_kind("unit")
def test_public_config_lifecycle_round_trips_active_snapshot() -> None:
    config = package.get_config()

    assert isinstance(config, LLMRouterConfig)
    assert package.install_config(config) is config
    assert package.get_config() is config

"""LLM Router public config boundary scenario.

Why:
    Verifies that the top-level package API can install and read the real
    product config snapshot end to end.
"""

from __future__ import annotations

from llm_router import LLMRouterConfig, get_config, install_config


def run_pipeline() -> LLMRouterConfig:
    """Install the active product config through the public API."""
    return install_config(get_config())


def assert_public_config_response(config: LLMRouterConfig) -> None:
    """Assert the installed public snapshot is returned unchanged."""
    assert get_config() is config


def test_public_config_pipeline() -> None:
    """The real config lifecycle works through the top-level package."""
    config = run_pipeline()
    assert_public_config_response(config)

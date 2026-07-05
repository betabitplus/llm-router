"""Public package boundary unit tests."""

from __future__ import annotations

import llm_router as package
from llm_router import LLMRouterConfig, LLMRouterError


def test_public_exports_resolve() -> None:
    """Every declared top-level public name resolves."""
    for name in package.__all__:
        assert hasattr(package, name)


def test_public_exception_is_package_specific() -> None:
    """The package exposes its established exception base."""
    assert issubclass(LLMRouterError, Exception)


def test_public_config_exports_resolve() -> None:
    """The package exposes the real immutable config lifecycle."""
    config = package.get_config()

    assert isinstance(config, LLMRouterConfig)
    assert package.install_config(config) is config


def test_version_is_available() -> None:
    """The package exposes distribution metadata or its source fallback."""
    assert package.__version__

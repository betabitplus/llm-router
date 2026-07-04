"""LLMRouter-specific test runtime helpers.

Why:
    Product tests need to reset installed runtime state between scenarios, but
    reusable support under `tests/support/` should not know LLMRouter APIs.
"""

from __future__ import annotations


def clear_test_caches() -> None:
    """Reset installed LLMRouter config caches between tests."""
    from llm_router import get_config, install_config

    install_config(get_config())

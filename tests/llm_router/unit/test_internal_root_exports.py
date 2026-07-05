"""Private-root boundary regression tests."""

from __future__ import annotations

import llm_router._internal as internal


def test_internal_root_uses_explicit_facade_without_public_all() -> None:
    """Keep private entrypoints narrow without presenting public API."""
    assert not hasattr(internal, "__all__")
    expected = {
        "BehaviorDefaults",
        "LLMRouterConfig",
        "ProviderCatalog",
        "ProviderSpec",
        "RetryPolicy",
        "RouterPolicyDefaults",
        "RouterRuntime",
        "SessionStore",
        "clear_adapter_caches",
        "get_config",
        "install_config",
    }
    assert expected <= set(vars(internal))


def test_internal_root_does_not_export_provider_adapters() -> None:
    """Do not leak concrete provider adapters through the root."""
    forbidden = {
        "AIStudioAdapter",
        "GeminiWebApiAdapter",
        "GoogleGenAIAdapter",
        "OpenAICompatibleAdapter",
        "QwenChatAdapter",
    }
    assert forbidden.isdisjoint(vars(internal))

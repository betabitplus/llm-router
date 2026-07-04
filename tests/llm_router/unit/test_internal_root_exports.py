def test_internal_root_exports_only_api_consumed_names() -> None:
    import llm_router._internal as internal

    expected_names = [
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
    ]

    assert internal.__all__ == expected_names
    for name in expected_names:
        assert hasattr(internal, name)


def test_internal_root_does_not_export_provider_adapter_internals() -> None:
    import llm_router._internal as internal

    blocked_names = {
        "ProviderAdapter",
        "ProviderRequest",
        "ProviderResult",
        "openai_compatible",
        "google_genai",
        "aistudio",
        "gemini_webapi",
        "qwenchat",
    }

    assert blocked_names.isdisjoint(internal.__all__)

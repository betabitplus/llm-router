from __future__ import annotations

import os
from dataclasses import replace

import pytest

from llm_router import ApiKeyNotFoundError, Provider
from llm_router._internal.config import build_default_config
from llm_router._internal.runtime.limiter import KeyResolver


def _clear_provider_keys(monkeypatch: pytest.MonkeyPatch, provider: Provider) -> None:
    prefix = f"{provider.name}_API_KEY_"
    for name in tuple(os.environ):
        if name.startswith(prefix):
            monkeypatch.delenv(name, raising=False)


pytestmark = [
    pytest.mark.verifies("REQ_CREDENTIAL_RESOLUTION[revision==1]"),
    pytest.mark.verification_kind("unit"),
]


@pytest.mark.coverage_item("VC_CREDENTIAL_CUSTOM_ENV_NAME")
def test_fixed_key_can_use_configured_custom_env_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = build_default_config()
    provider_specs = dict(config.catalog.providers)
    provider_specs[Provider.NVIDIA] = replace(
        provider_specs[Provider.NVIDIA],
        api_key_env_vars={4: "CUSTOM_NVIDIA_KEY"},
    )
    config = replace(config, catalog=replace(config.catalog, providers=provider_specs))
    monkeypatch.setenv("CUSTOM_NVIDIA_KEY", "custom-value")

    resolved = KeyResolver(config).resolve(provider=Provider.NVIDIA, key_id=4)

    assert (resolved.key_id, resolved.env_var, resolved.value) == (
        4,
        "CUSTOM_NVIDIA_KEY",
        "custom-value",
    )


@pytest.mark.coverage_item("VC_CREDENTIAL_AUTO_ROTATION")
def test_auto_key_rotation_uses_sorted_available_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = build_default_config()
    _clear_provider_keys(monkeypatch, Provider.NVIDIA)
    monkeypatch.setenv("NVIDIA_API_KEY_2", "key-2")
    monkeypatch.setenv("NVIDIA_API_KEY_1", "key-1")
    resolver = KeyResolver(config)

    resolved = [
        resolver.resolve(provider=Provider.NVIDIA, key_id="auto") for _ in range(3)
    ]

    assert [key.key_id for key in resolved] == [1, 2, 1]


@pytest.mark.coverage_item("VC_CREDENTIAL_AUTO_ROTATION")
def test_auto_key_rotation_uses_configured_custom_key_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = build_default_config()
    _clear_provider_keys(monkeypatch, Provider.NVIDIA)
    provider_specs = dict(config.catalog.providers)
    provider_specs[Provider.NVIDIA] = replace(
        provider_specs[Provider.NVIDIA],
        api_key_env_vars={3: "CUSTOM_NVIDIA_3", 1: "CUSTOM_NVIDIA_1"},
    )
    config = replace(config, catalog=replace(config.catalog, providers=provider_specs))
    monkeypatch.setenv("CUSTOM_NVIDIA_3", "key-3")
    monkeypatch.setenv("CUSTOM_NVIDIA_1", "key-1")
    resolver = KeyResolver(config)

    resolved = [
        resolver.resolve(provider=Provider.NVIDIA, key_id="auto") for _ in range(3)
    ]

    assert [key.key_id for key in resolved] == [1, 3, 1]
    assert [key.env_var for key in resolved] == [
        "CUSTOM_NVIDIA_1",
        "CUSTOM_NVIDIA_3",
        "CUSTOM_NVIDIA_1",
    ]


@pytest.mark.coverage_item("VC_CREDENTIAL_REQUIRED_MISSING")
def test_missing_required_key_raises_public_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = build_default_config()
    _clear_provider_keys(monkeypatch, Provider.NVIDIA)

    with pytest.raises(ApiKeyNotFoundError) as exc_info:
        KeyResolver(config).resolve(provider=Provider.NVIDIA, key_id=9)

    assert exc_info.value.key_name == "NVIDIA_API_KEY_9"
    assert exc_info.value.provider == Provider.NVIDIA.value


@pytest.mark.coverage_item("VC_CREDENTIAL_OPTIONAL_MISSING")
@pytest.mark.parametrize("provider", [Provider.QWENCHAT, Provider.GEMINI_WEBAPI])
def test_optional_provider_key_can_resolve_to_empty_bearer(
    monkeypatch: pytest.MonkeyPatch,
    provider: Provider,
) -> None:
    config = build_default_config()
    _clear_provider_keys(monkeypatch, provider)

    resolved = KeyResolver(config).resolve(provider=provider, key_id="auto")

    assert resolved.key_id == config.default_key_id
    assert resolved.value == ""

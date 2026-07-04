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


def test_fixed_key_uses_generated_provider_env_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = build_default_config()
    _clear_provider_keys(monkeypatch, Provider.NVIDIA)
    monkeypatch.setenv("NVIDIA_API_KEY_3", "nvidia-key-3")

    resolved = KeyResolver(config).resolve(provider=Provider.NVIDIA, key_id=3)

    assert resolved.key_id == 3
    assert resolved.env_var == "NVIDIA_API_KEY_3"
    assert resolved.value == "nvidia-key-3"


def test_fixed_key_uses_configured_custom_env_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = build_default_config()
    provider_specs = dict(config.catalog.providers)
    provider_specs[Provider.NVIDIA] = replace(
        provider_specs[Provider.NVIDIA],
        api_key_env_vars={4: "CUSTOM_NVIDIA_KEY"},
    )
    custom_config = replace(
        config,
        catalog=replace(config.catalog, providers=provider_specs),
    )
    monkeypatch.setenv("CUSTOM_NVIDIA_KEY", "custom-value")

    resolved = KeyResolver(custom_config).resolve(provider=Provider.NVIDIA, key_id=4)

    assert resolved.key_id == 4
    assert resolved.env_var == "CUSTOM_NVIDIA_KEY"
    assert resolved.value == "custom-value"


def test_auto_key_rotation_uses_sorted_configured_and_discovered_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = build_default_config()
    _clear_provider_keys(monkeypatch, Provider.NVIDIA)
    monkeypatch.setenv("NVIDIA_API_KEY_2", "nvidia-key-2")
    monkeypatch.setenv("NVIDIA_API_KEY_1", "nvidia-key-1")
    resolver = KeyResolver(config)

    first = resolver.resolve(provider=Provider.NVIDIA, key_id="auto")
    second = resolver.resolve(provider=Provider.NVIDIA, key_id="auto")
    third = resolver.resolve(provider=Provider.NVIDIA, key_id="auto")

    assert [first.key_id, second.key_id, third.key_id] == [1, 2, 1]
    assert [first.value, second.value, third.value] == [
        "nvidia-key-1",
        "nvidia-key-2",
        "nvidia-key-1",
    ]


def test_missing_key_raises_public_configuration_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = build_default_config()
    _clear_provider_keys(monkeypatch, Provider.NVIDIA)

    with pytest.raises(ApiKeyNotFoundError) as exc_info:
        KeyResolver(config).resolve(provider=Provider.NVIDIA, key_id=9)

    assert exc_info.value.key_name == "NVIDIA_API_KEY_9"
    assert exc_info.value.provider == Provider.NVIDIA.value
    assert exc_info.value.key_id == 9


def test_qwenchat_missing_key_resolves_empty_optional_bearer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = build_default_config()
    _clear_provider_keys(monkeypatch, Provider.QWENCHAT)

    resolved = KeyResolver(config).resolve(provider=Provider.QWENCHAT, key_id=1)

    assert resolved.key_id == 1
    assert resolved.env_var == "QWENCHAT_API_KEY_1"
    assert resolved.value == ""


def test_qwenchat_auto_key_without_env_uses_default_empty_bearer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = build_default_config()
    _clear_provider_keys(monkeypatch, Provider.QWENCHAT)

    resolved = KeyResolver(config).resolve(provider=Provider.QWENCHAT, key_id="auto")

    assert resolved.key_id == 1
    assert resolved.env_var == "QWENCHAT_API_KEY_1"
    assert resolved.value == ""

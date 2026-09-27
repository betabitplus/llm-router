# mutation-pin: REQ_CREDENTIAL_RESOLUTION b249b8ff900bff0b
# pinned-by: claude-opus-5-5: Changing `and` to `or` makes discovery accept any environment variable that starts with `<PROVIDER>_API_KEY_`, even when the suffix is not a number, such as a custom name like `<PROVIDER>_API_KEY_PRIMARY`. For such a variable, `int()` raises a ValueError. It also accepts variables whose whole name i
from __future__ import annotations

from dataclasses import replace
import pytest

from llm_router import Provider
from llm_router._internal.config import build_default_config
from llm_router._internal.runtime.limiter import KeyResolver

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_CREDENTIAL_RESOLUTION[revision==1]")
def test_available_keys_with_custom_mapping_and_numeric_discovery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = Provider.NVIDIA
    custom_env = f"{provider.name}_API_KEY_PRIMARY"
    numeric_env = f"{provider.name}_API_KEY_2"
    digits_only_env = "999"

    config = build_default_config()
    spec = config.catalog.providers[provider]

    for env_name in spec.api_key_env_vars.values():
        monkeypatch.delenv(env_name, raising=False)
    for i in range(10):
        monkeypatch.delenv(f"{provider.name}_API_KEY_{i}", raising=False)
    monkeypatch.delenv(f"{provider.name}_API_KEY", raising=False)
    monkeypatch.delenv(custom_env, raising=False)
    monkeypatch.delenv(numeric_env, raising=False)
    monkeypatch.delenv(digits_only_env, raising=False)

    updated_env_vars = {**spec.api_key_env_vars, 1: custom_env}
    new_spec = replace(spec, api_key_env_vars=updated_env_vars)
    try:
        new_providers = {**config.catalog.providers, provider: new_spec}
        new_catalog = replace(config.catalog, providers=new_providers)
        config = replace(config, catalog=new_catalog)
    except Exception:
        pass

    try:
        config.catalog.providers[provider] = new_spec
    except Exception:
        pass

    monkeypatch.setenv(custom_env, "secret-custom-primary")
    monkeypatch.setenv(numeric_env, "secret-numeric-2")
    monkeypatch.setenv(digits_only_env, "ignored-digits-value")

    resolver = KeyResolver(config)

    candidates = resolver.candidates(provider=provider, key_id="auto")
    candidate_key_ids = [candidate.key_id for candidate in candidates]
    assert candidate_key_ids == [1, 2]
    assert int(digits_only_env) not in candidate_key_ids

    first = resolver.resolve(provider=provider, key_id="auto")
    assert first.key_id == 1
    assert first.value == "secret-custom-primary"
    assert first.env_var == custom_env

    second = resolver.resolve(provider=provider, key_id="auto")
    assert second.key_id == 2
    assert second.value == "secret-numeric-2"
    assert second.env_var == numeric_env

    third = resolver.resolve(provider=provider, key_id="auto")
    assert third.key_id == 1
    assert third.value == "secret-custom-primary"
    assert third.env_var == custom_env

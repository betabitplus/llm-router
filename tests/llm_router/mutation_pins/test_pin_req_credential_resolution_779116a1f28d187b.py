# mutation-pin: REQ_CREDENTIAL_RESOLUTION 779116a1f28d187b
# pinned-by: claude-opus-5-5: The requirement says a configured fixed key must resolve through its configured custom environment name. The mutant breaks this: for the default key ID, a provider configured with api_key_env_var='CUSTOM_KEY' resolves to GOOGLE_API_KEY_0 instead of CUSTOM_KEY, and this was confirmed by running it. N
from __future__ import annotations

from dataclasses import replace
import pytest

from llm_router import Provider
from llm_router._internal.config import build_default_config
from llm_router._internal.runtime.limiter import KeyResolver

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_CREDENTIAL_RESOLUTION[revision==1]")
def test_configured_fixed_key_resolves_custom_and_default_naming(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_config = build_default_config()
    provider = Provider.GOOGLE
    spec = replace(
        base_config.catalog.providers[provider],
        api_key_env_var="CUSTOM_KEY",
        api_key_env_vars={},
    )
    providers = dict(base_config.catalog.providers)
    providers[provider] = spec
    catalog = replace(base_config.catalog, providers=providers)
    config = replace(base_config, catalog=catalog)

    resolver = KeyResolver(config)
    default_key_id = config.default_key_id
    non_default_key_id = default_key_id + 1

    custom_env = "CUSTOM_KEY"
    standard_env = f"{provider.name}_API_KEY_{non_default_key_id}"
    monkeypatch.setenv(custom_env, "custom-secret-key")
    monkeypatch.setenv(standard_env, "standard-secret-key")

    assert resolver._key_name(provider=provider, key_id=default_key_id) == custom_env
    assert (
        resolver._key_name(provider=provider, key_id=non_default_key_id)
        == standard_env
    )

    resolved_default = resolver.resolve(provider=provider, key_id=default_key_id)
    assert resolved_default.env_var == custom_env
    assert resolved_default.value == "custom-secret-key"

    resolved_non_default = resolver.resolve(
        provider=provider, key_id=non_default_key_id
    )
    assert resolved_non_default.env_var == standard_env
    assert resolved_non_default.value == "standard-secret-key"

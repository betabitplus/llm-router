# mutation-pin: REQ_CREDENTIAL_RESOLUTION 8bf6ec5f1367a5d6
# pinned-by: claude-opus-5-5
from __future__ import annotations

from dataclasses import replace

import pytest

from llm_router import Provider
from llm_router._internal.config import build_default_config
from llm_router._internal.runtime.limiter import KeyResolver, ResolvedKey

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_CREDENTIAL_RESOLUTION[revision==1]")
def test_configured_fixed_candidate_resolves_custom_environment_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ident = 2
    env_var = "CUSTOM_NVIDIA_AUTH"
    value = "mock_auth_value"
    monkeypatch.setenv(env_var, value)

    config = build_default_config()
    provider_spec = replace(
        config.catalog.providers[Provider.NVIDIA],
        api_key_env_vars={
            **config.catalog.providers[Provider.NVIDIA].api_key_env_vars,
            ident: env_var,
        },
    )
    catalog = replace(
        config.catalog,
        providers={**config.catalog.providers, Provider.NVIDIA: provider_spec},
    )
    config = replace(config, catalog=catalog)

    resolver = KeyResolver(config)
    result = resolver.candidates(provider=Provider.NVIDIA, key_id=ident)

    expected = (ResolvedKey(key_id=ident, env_var=env_var, value=value),)
    assert result == expected
    assert len(result) == 1
    assert result[0].key_id == ident
    assert result[0].env_var == env_var
    assert result[0].value == value

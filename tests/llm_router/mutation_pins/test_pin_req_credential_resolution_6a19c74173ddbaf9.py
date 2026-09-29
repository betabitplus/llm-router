# mutation-pin: REQ_CREDENTIAL_RESOLUTION 6a19c74173ddbaf9
# pinned-by: claude-opus-5-5
from __future__ import annotations

from dataclasses import replace

import pytest

from llm_router import Provider
from llm_router._internal.config import build_default_config
from llm_router._internal.runtime.limiter import KeyResolver, ResolvedKey

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_CREDENTIAL_RESOLUTION[revision==1]")
def test_auto_candidates_is_reusable_tuple(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Auto candidates must be a concrete tuple, iterable repeatedly."""
    provider = Provider.NVIDIA
    prefix = f"{provider.name}_API_KEY_"
    custom_env = f"{prefix}PRIMARY"
    config = build_default_config()
    spec = config.catalog.providers[provider]
    for env_name in spec.api_key_env_vars.values():
        monkeypatch.delenv(env_name, raising=False)
    new_spec = replace(spec, api_key_env_vars={1: custom_env})
    catalog = replace(
        config.catalog,
        providers={**config.catalog.providers, provider: new_spec},
    )
    config = replace(config, catalog=catalog)
    monkeypatch.setenv(custom_env, "resolved-primary")

    resolver = KeyResolver(config)
    result = resolver.candidates(provider=provider, key_id="auto")

    assert isinstance(result, tuple)
    first = [c.key_id for c in result]
    second = [c.key_id for c in result]
    assert first == second
    assert 1 in first
    assert all(isinstance(c, ResolvedKey) for c in result)
    primary = next(iter(c for c in result if c.key_id == 1))
    assert primary.env_var == custom_env
    assert primary.value == "resolved-primary"

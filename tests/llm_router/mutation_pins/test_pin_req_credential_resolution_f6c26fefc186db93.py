# mutation-pin: REQ_CREDENTIAL_RESOLUTION f6c26fefc186db93
# pinned-by: claude-opus-5-5
from __future__ import annotations

from dataclasses import replace

import pytest

from llm_router import Provider
from llm_router._internal.config import build_default_config
from llm_router._internal.runtime.limiter import KeyResolver

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_CREDENTIAL_RESOLUTION[revision==1]")
def test_auto_key_rotation_order_and_preference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = "test-credential"
    monkeypatch.setenv("ENV_A", value)
    monkeypatch.setenv("ENV_B", value)
    monkeypatch.setenv("ENV_C", value)

    config = build_default_config()
    env_map = {1: "ENV_A", 2: "ENV_B", 3: "ENV_C"}
    spec = replace(
        config.catalog.providers[Provider.GOOGLE],
        api_key_env_var=None,
        api_key_env_vars=env_map,
    )
    catalog = replace(
        config.catalog,
        providers={**config.catalog.providers, Provider.GOOGLE: spec},
    )
    config = replace(config, catalog=catalog)

    resolver = KeyResolver(config)
    auto_mode = "auto"

    first = resolver.resolve(provider=Provider.GOOGLE, key_id=auto_mode)
    second = resolver.resolve(provider=Provider.GOOGLE, key_id=auto_mode)
    third = resolver.resolve(provider=Provider.GOOGLE, key_id=auto_mode)
    fourth = resolver.resolve(provider=Provider.GOOGLE, key_id=auto_mode)

    assert [first.key_id, second.key_id, third.key_id, fourth.key_id] == [
        1,
        2,
        3,
        1,
    ]

    pref_resolver = KeyResolver(config)
    pref_ids = {2, 3}
    pref_first = pref_resolver.resolve(
        provider=Provider.GOOGLE,
        key_id=auto_mode,
        preferred_key_ids=pref_ids,
    )
    pref_second = pref_resolver.resolve(
        provider=Provider.GOOGLE,
        key_id=auto_mode,
        preferred_key_ids=pref_ids,
    )

    assert pref_first.key_id == 2
    assert pref_second.key_id == 3

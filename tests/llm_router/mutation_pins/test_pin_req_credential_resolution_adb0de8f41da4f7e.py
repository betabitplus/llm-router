# mutation-pin: REQ_CREDENTIAL_RESOLUTION adb0de8f41da4f7e
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router import Provider
from llm_router._internal.config import build_default_config
from llm_router._internal.runtime.limiter import (
    KeyResolver,
    ResolvedKey,
    _allows_missing_key,
)

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_CREDENTIAL_RESOLUTION[revision==1]")
def test_candidates_auto_with_missing_key_permitted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = build_default_config()
    missing_key_providers = [
        provider for provider in Provider if _allows_missing_key(provider)
    ]
    assert missing_key_providers

    for provider in missing_key_providers:
        spec = config.catalog.providers[provider]
        for env_name in spec.api_key_env_vars.values():
            monkeypatch.delenv(env_name, raising=False)

        resolver = KeyResolver(config)
        expected_env = resolver._key_name(
            provider=provider, key_id=config.default_key_id
        )
        monkeypatch.delenv(expected_env, raising=False)

        candidates = resolver.candidates(provider=provider, key_id="auto")
        assert candidates == (
            ResolvedKey(
                key_id=config.default_key_id,
                env_var=expected_env,
                value="",
            ),
        )

# mutation-pin: REQ_CREDENTIAL_RESOLUTION b30cea8391ac9160
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
def test_missing_optional_credential_resolves_empty_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = build_default_config()
    provider = next(p for p in Provider if _allows_missing_key(p))
    fixed_id = 9
    resolver = KeyResolver(config)
    var_name = resolver._key_name(provider=provider, key_id=fixed_id)
    monkeypatch.delenv(var_name, raising=False)

    resolved = resolver.resolve(provider=provider, key_id=fixed_id)

    assert resolved == ResolvedKey(
        key_id=fixed_id,
        env_var=var_name,
        value="",
    )
    assert resolved.key_id == fixed_id
    assert resolved.env_var == var_name
    assert resolved.value == ""

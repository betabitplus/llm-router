# mutation-pin: REQ_CREDENTIAL_RESOLUTION 5ef3f33a9ec29e3d
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router import ApiKeyNotFoundError, Provider
from llm_router._internal.config import build_default_config
from llm_router._internal.runtime.limiter import KeyResolver

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_CREDENTIAL_RESOLUTION[revision==1]")
def test_candidates_missing_required_key_raises_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = build_default_config()
    resolver = KeyResolver(config)
    spec = config.catalog.providers[Provider.NVIDIA]
    for env_name in spec.api_key_env_vars.values():
        monkeypatch.delenv(env_name, raising=False)
    for candidate_id in range(10):
        monkeypatch.delenv(
            resolver._key_name(provider=Provider.NVIDIA, key_id=candidate_id),
            raising=False,
        )
    expected_env_var = resolver._key_name(
        provider=Provider.NVIDIA, key_id=config.default_key_id
    )
    mode = "auto"

    with pytest.raises(ApiKeyNotFoundError) as exc_info:
        resolver.candidates(provider=Provider.NVIDIA, key_id=mode)

    assert exc_info.value.key_name == expected_env_var
    assert exc_info.value.provider == Provider.NVIDIA.value
    assert exc_info.value.key_id == config.default_key_id

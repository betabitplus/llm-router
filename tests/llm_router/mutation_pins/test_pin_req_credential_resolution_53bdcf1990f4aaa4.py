# mutation-pin: REQ_CREDENTIAL_RESOLUTION 53bdcf1990f4aaa4
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router import ApiKeyNotFoundError, Provider
from llm_router._internal.config import build_default_config
from llm_router._internal.runtime.limiter import KeyResolver

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_CREDENTIAL_RESOLUTION[revision==1]")
def test_auto_resolution_missing_required_key_raises_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = build_default_config()
    spec = config.catalog.providers[Provider.NVIDIA]
    for env_name in spec.api_key_env_vars.values():
        monkeypatch.delenv(env_name, raising=False)

    selection_mode = "auto"
    resolver = KeyResolver(config)
    with pytest.raises(ApiKeyNotFoundError) as exc_info:
        resolver.resolve(provider=Provider.NVIDIA, key_id=selection_mode)

    expected_name = spec.api_key_env_vars[config.default_key_id]
    assert exc_info.value.key_name == expected_name
    assert exc_info.value.provider == Provider.NVIDIA.value
    assert exc_info.value.key_id == config.default_key_id

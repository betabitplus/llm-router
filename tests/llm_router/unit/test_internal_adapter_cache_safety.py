from __future__ import annotations

from dataclasses import replace

import pytest

from llm_router._api.config import get_config, install_config
from llm_router._internal.providers.registry import register_adapter_cache

pytestmark = [
    pytest.mark.verifies("TREQ_CONFIG_CACHE_INVALIDATION[revision==1]"),
    pytest.mark.verification_kind("unit"),
]


@pytest.mark.coverage_item("VC_CONFIG_CACHE_INVALIDATION")
def test_install_config_invalidates_registered_adapter_caches() -> None:
    current = get_config()
    replacement = replace(current, default_key_id=current.default_key_id + 1)
    cache: dict[str, object] = {"stale": object()}
    register_adapter_cache(cache)

    install_config(replacement)

    assert cache == {}

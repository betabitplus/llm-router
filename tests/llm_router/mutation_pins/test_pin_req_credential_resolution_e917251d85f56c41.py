# mutation-pin: REQ_CREDENTIAL_RESOLUTION e917251d85f56c41
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router import Provider
from llm_router._internal.config import build_default_config
from llm_router._internal.runtime.limiter import KeyResolver

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_CREDENTIAL_RESOLUTION[revision==1]")
def test_auto_rotation_wraps_around_for_preferred_ids(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = build_default_config()
    for index in range(25):
        monkeypatch.delenv(f"NVIDIA_API_KEY_{index}", raising=False)
    monkeypatch.setenv("NVIDIA_API_KEY_1", "alpha")
    monkeypatch.setenv("NVIDIA_API_KEY_2", "beta")
    monkeypatch.setenv("NVIDIA_API_KEY_3", "gamma")
    resolver = KeyResolver(config)

    first = resolver.resolve(provider=Provider.NVIDIA, key_id="auto")
    selected = resolver.resolve(
        provider=Provider.NVIDIA,
        key_id="auto",
        preferred_key_ids={1},
    )

    assert first.key_id == 1
    assert selected.key_id == 1

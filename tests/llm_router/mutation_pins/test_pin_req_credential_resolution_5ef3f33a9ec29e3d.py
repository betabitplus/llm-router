# mutation-pin: REQ_CREDENTIAL_RESOLUTION 5ef3f33a9ec29e3d
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import pytest

from llm_router import ApiKeyNotFoundError, LLMRouter, Model, Provider, RouterProfile

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_CREDENTIAL_RESOLUTION[revision==1]")
def test_auto_request_without_any_key_raises_missing_key_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prefix = "OPENROUTER_API_KEY"
    monkeypatch.delenv(prefix, raising=False)
    for number in range(100):
        monkeypatch.delenv(f"{prefix}_{number}", raising=False)
    router = LLMRouter(
        RouterProfile(model=Model.DEEPSEEK_V3, provider=Provider.OPENROUTER),
        key_id="auto",
        temperature=0.0,
        seed=1,
    )

    with pytest.raises(ApiKeyNotFoundError, match=r"OPENROUTER_API_KEY") as info:
        router.query("Reply with one word.")

    assert info.value.provider == Provider.OPENROUTER.value
    assert info.value.key_name.startswith(prefix)
    assert isinstance(info.value.key_id, int)

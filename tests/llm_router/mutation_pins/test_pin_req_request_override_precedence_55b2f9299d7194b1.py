# mutation-pin: REQ_REQUEST_OVERRIDE_PRECEDENCE 55b2f9299d7194b1
# pinned-by: claude-opus-5-5
# written-by: claude-opus-5-5, the last resort, the verdict's own model with tools
from __future__ import annotations

import pytest

from llm_router import (
    ApiKeyNotFoundError,
    LLMRouter,
    LLMRouterConfig,
    Model,
    Provider,
    RouterProfile,
    get_config,
    install_config,
)

pytestmark = pytest.mark.verification_kind("unit")


@pytest.fixture
def config_without_default_key_id(monkeypatch: pytest.MonkeyPatch) -> object:
    previous = get_config()
    for suffix in ("None", "2"):
        monkeypatch.delenv(f"OPENROUTER_API_KEY_{suffix}", raising=False)
    unset_key_id = None
    config = LLMRouterConfig(
        default_provider=previous.default_provider,
        default_model=previous.default_model,
        default_key_id=unset_key_id,  # type: ignore[arg-type]
        defaults=previous.defaults,
        catalog=previous.catalog,
    )
    yield install_config(config)
    install_config(previous)


@pytest.mark.verifies("REQ_REQUEST_OVERRIDE_PRECEDENCE[revision==1]")
def test_unset_route_key_id_stays_none_without_router_or_call_override(
    config_without_default_key_id: LLMRouterConfig,
) -> None:
    assert config_without_default_key_id.default_key_id is None
    router = LLMRouter(
        RouterProfile(provider=Provider.OPENROUTER, model=Model.DEEPSEEK_V3),
    )

    with pytest.raises(ApiKeyNotFoundError, match=r"OPENROUTER_API_KEY_None") as info:
        router.query("Say hello.")

    assert info.value.key_id is None
    assert info.value.provider == Provider.OPENROUTER.value


@pytest.mark.verifies("REQ_REQUEST_OVERRIDE_PRECEDENCE[revision==1]")
def test_router_key_id_fills_unset_route_key_id(
    config_without_default_key_id: LLMRouterConfig,
) -> None:
    assert config_without_default_key_id.default_key_id is None
    router = LLMRouter(
        RouterProfile(provider=Provider.OPENROUTER, model=Model.DEEPSEEK_V3),
        key_id=2,
    )

    with pytest.raises(ApiKeyNotFoundError, match=r"OPENROUTER_API_KEY_2") as info:
        router.query("Say hello.", temperature=None)

    assert info.value.key_id == 2

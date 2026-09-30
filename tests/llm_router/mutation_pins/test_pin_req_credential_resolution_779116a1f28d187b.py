# mutation-pin: REQ_CREDENTIAL_RESOLUTION 779116a1f28d187b
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

from dataclasses import replace

import pytest

import llm_router as package
from llm_router import (
    ApiKeyNotFoundError,
    LLMRouter,
    Model,
    Provider,
    RouterProfile,
)

pytestmark = pytest.mark.verification_kind("unit")

PROVIDER = Provider.OPENROUTER
CUSTOM_ENV = "CUSTOM_ROUTER_CREDENTIAL"


def _missing_key_name(key_id: int) -> str:
    router = LLMRouter(
        RouterProfile(model=Model.DEEPSEEK_V3, provider=PROVIDER, key_id=key_id)
    )
    with pytest.raises(ApiKeyNotFoundError, match=r".+") as exc_info:
        router.query("hello")
    return exc_info.value.key_name


@pytest.mark.verifies("REQ_CREDENTIAL_RESOLUTION[revision==1]")
def test_custom_env_name_applies_only_to_default_key_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = package.get_config()
    default_id = original.default_key_id
    other_id = default_id + 1
    spec = replace(
        original.catalog.providers[PROVIDER],
        api_key_env_var=CUSTOM_ENV,
        api_key_env_vars={},
    )
    providers = dict(original.catalog.providers)
    providers[PROVIDER] = spec
    catalog = replace(original.catalog, providers=providers)
    monkeypatch.delenv(CUSTOM_ENV, raising=False)
    monkeypatch.delenv(f"{PROVIDER.name}_API_KEY_{default_id}", raising=False)
    monkeypatch.delenv(f"{PROVIDER.name}_API_KEY_{other_id}", raising=False)

    package.install_config(replace(original, catalog=catalog))
    default_name = _missing_key_name(default_id)
    other_name = _missing_key_name(other_id)
    package.install_config(original)

    assert default_name == CUSTOM_ENV
    assert other_name == f"{PROVIDER.name}_API_KEY_{other_id}"

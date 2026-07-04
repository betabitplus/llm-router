from __future__ import annotations

import pytest

from llm_router import Model, Provider, install_config as public_install_config
from llm_router._internal.capabilities.content import normalize_content
from llm_router._internal.config import build_default_config
from llm_router._internal.providers import registry as provider_registry
from llm_router._internal.providers.base import (
    ProviderCapabilities,
    ProviderCredential,
    ProviderRequest,
    ProviderResult,
)
from llm_router._internal.providers.openai_compatible import OpenAICompatibleAdapter
from llm_router._internal.providers.registry import (
    clear_adapter_caches,
    get_adapter,
    register_adapter_cache,
    register_adapter_factory,
)


@pytest.fixture(autouse=True)
def restore_provider_registry() -> object:
    factories = dict(provider_registry._adapter_factories)
    clear_adapter_caches()
    yield
    provider_registry._adapter_factories.clear()
    provider_registry._adapter_factories.update(factories)
    clear_adapter_caches()


class DummyAdapter:
    capabilities = ProviderCapabilities()

    def __init__(self, provider: Provider) -> None:
        self.provider = provider

    def execute(self, request: ProviderRequest) -> ProviderResult:
        return ProviderResult(
            data={},
            provider=request.provider,
            model=request.model,
            provider_model=request.provider_model,
            output_text="",
        )

    async def aexecute(self, request: ProviderRequest) -> ProviderResult:
        return self.execute(request)


def _request() -> ProviderRequest:
    return ProviderRequest(
        request_id="req-1",
        provider=Provider.OPENROUTER,
        model=Model.DEEPSEEK_V3,
        provider_model="deepseek/test",
        credential=ProviderCredential(
            key_id=1,
            env_var="OPENROUTER_API_KEY_1",
            value="secret",
        ),
        messages=[normalize_content("hello")],
        kwargs={"logprobs": True},
    )


def test_provider_request_and_result_copy_mutable_inputs() -> None:
    request_kwargs = {"logprobs": True}
    request = ProviderRequest(
        request_id="req-1",
        provider=Provider.OPENROUTER,
        model=Model.DEEPSEEK_V3,
        provider_model="deepseek/test",
        credential=ProviderCredential(
            key_id=1,
            env_var="OPENROUTER_API_KEY_1",
            value="secret",
        ),
        messages=[normalize_content("hello")],
        kwargs=request_kwargs,
    )
    request_kwargs["logprobs"] = False
    data = {"id": "response"}
    result = ProviderResult(
        data=data,
        provider=Provider.OPENROUTER,
        model=Model.DEEPSEEK_V3,
        provider_model="deepseek/test",
        output_text="ok",
    )
    data["id"] = "mutated"

    assert request.kwargs == {"logprobs": True}
    assert result.data == {"id": "response"}


def test_registry_caches_by_config_snapshot_and_provider() -> None:
    config = build_default_config()
    created: list[Provider] = []

    def factory(_config, provider: Provider) -> DummyAdapter:
        created.append(provider)
        return DummyAdapter(provider)

    register_adapter_factory(Provider.GEMINI_WEBAPI, factory)
    first = get_adapter(provider=Provider.GEMINI_WEBAPI, config=config)
    second = get_adapter(provider=Provider.GEMINI_WEBAPI, config=config)

    assert first is second
    assert created == [Provider.GEMINI_WEBAPI]


def test_registry_cache_key_includes_config_snapshot_and_provider() -> None:
    first_config = build_default_config()
    second_config = build_default_config()
    created: list[Provider] = []

    def factory(_config, provider: Provider) -> DummyAdapter:
        created.append(provider)
        return DummyAdapter(provider)

    register_adapter_factory(Provider.GEMINI_WEBAPI, factory)
    register_adapter_factory(Provider.QWENCHAT, factory)
    first = get_adapter(provider=Provider.GEMINI_WEBAPI, config=first_config)
    second = get_adapter(provider=Provider.GEMINI_WEBAPI, config=second_config)
    third = get_adapter(provider=Provider.QWENCHAT, config=first_config)

    assert first is not second
    assert first is not third
    assert created == [
        Provider.GEMINI_WEBAPI,
        Provider.GEMINI_WEBAPI,
        Provider.QWENCHAT,
    ]


def test_registry_has_built_in_openai_compatible_factory() -> None:
    config = build_default_config()
    clear_adapter_caches()

    adapter = get_adapter(provider=Provider.GROQ, config=config)

    assert isinstance(adapter, OpenAICompatibleAdapter)
    assert adapter.base_url == "https://api.groq.com/openai/v1"


def test_registry_missing_factory_has_provider_name() -> None:
    config = build_default_config()
    provider_registry._adapter_factories.pop(Provider.GEMINI_WEBAPI, None)

    with pytest.raises(KeyError, match="gemini_webapi"):
        get_adapter(provider=Provider.GEMINI_WEBAPI, config=config)


def test_clear_adapter_caches_clears_registry_and_registered_caches() -> None:
    config = build_default_config()
    external_cache = {"client": object()}

    register_adapter_cache(external_cache)
    register_adapter_factory(
        Provider.QWENCHAT,
        lambda _config, provider: DummyAdapter(provider),
    )
    first = get_adapter(provider=Provider.QWENCHAT, config=config)

    clear_adapter_caches()
    second = get_adapter(provider=Provider.QWENCHAT, config=config)

    assert external_cache == {}
    assert second is not first


def test_public_install_config_clears_adapter_caches() -> None:
    original = build_default_config()
    external_cache = {"client": object()}
    register_adapter_cache(external_cache)

    public_install_config(original)

    assert external_cache == {}


def test_provider_request_helper_shape_is_stable() -> None:
    request = _request()

    assert request.messages[0].parts[0].kind == "text"
    assert request.kwargs == {"logprobs": True}

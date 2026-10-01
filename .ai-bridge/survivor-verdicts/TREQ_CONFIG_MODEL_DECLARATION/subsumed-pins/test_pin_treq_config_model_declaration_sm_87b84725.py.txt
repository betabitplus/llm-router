# mutation-pin: TREQ_CONFIG_MODEL_DECLARATION SM-87B84725
# pinned-by: claude-opus-5-5 and gemini-3.1-pro-high
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import typing
from dataclasses import dataclass, replace

import pytest

from llm_router import Model, Provider, ProviderCatalog
from llm_router._internal.config import build_default_config
from llm_router._internal.runtime.routes import expand_route_plan

pytestmark = pytest.mark.verification_kind("unit")


class EnumKeyedModels(typing.Mapping[Model, typing.Mapping[Provider, str]]):
    """Registry that only recognises real Model members as declared."""

    def __init__(self, data: typing.Mapping[Model, typing.Mapping[Provider, str]]):
        self._data = dict(data)

    def __getitem__(self, key: Model) -> typing.Mapping[Provider, str]:
        return self._data[key]

    def __iter__(self) -> typing.Iterator[Model]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __contains__(self, key: object) -> bool:
        return isinstance(key, Model) and key in self._data


@dataclass(frozen=True)
class EnumKeyedCatalog(ProviderCatalog):
    """Catalog whose model registry is keyed strictly by Model members."""

    def __post_init__(self) -> None:
        ProviderCatalog.__post_init__(self)
        object.__setattr__(self, "models", EnumKeyedModels(self.models))


@pytest.mark.verifies("TREQ_CONFIG_MODEL_DECLARATION[revision==1]")
def test_declared_model_given_as_string_is_accepted() -> None:
    base = build_default_config()
    catalog = EnumKeyedCatalog(
        providers=base.catalog.providers,
        provider_base_urls=base.catalog.provider_base_urls,
        models=base.catalog.models,
    )
    config = replace(base, catalog=catalog)
    declared = next(iter(config.models))

    plan = expand_route_plan(declared.value, config=config)

    assert plan.routes
    assert all(route.model is declared for route in plan.routes)

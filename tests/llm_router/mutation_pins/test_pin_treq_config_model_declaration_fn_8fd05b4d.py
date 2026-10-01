# mutation-pin: TREQ_CONFIG_MODEL_DECLARATION FN-8FD05B4D
# pinned-by: delegate, one pin for 5 pins of _resolve_model
# kills: 3cc16a6300b216ed 5ed9365a38636da5 SM-87B84725 SM-8D7935BF e1379ec0c0ed9e96
from __future__ import annotations

import typing
from dataclasses import dataclass, replace

import pytest

from llm_router import Model, Provider, ProviderCatalog
from llm_router._api.errors import ConfigurationError
from llm_router._api.types import RouterProfile
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
def test_only_declared_models_are_accepted() -> None:
    base = build_default_config()
    declared = base.default_model
    undeclared = next(iter(m for m in Model if m != declared))
    catalog = EnumKeyedCatalog(
        providers=base.catalog.providers,
        provider_base_urls=base.catalog.provider_base_urls,
        models={declared: base.models[declared]},
    )
    config = replace(base, catalog=catalog)
    assert undeclared not in config.models

    for spec in (declared, declared.value):
        plan = expand_route_plan(spec, config=config)
        assert plan.routes
        for route in plan.routes:
            assert isinstance(route.model, Model)
            assert route.model is declared

    declared_profile = RouterProfile(model=declared.value, provider="custom-route")
    plan = expand_route_plan(declared_profile, config=config)
    assert plan.routes
    assert all(route.model is declared for route in plan.routes)

    undeclared_str_profile = RouterProfile(
        model=undeclared.value, provider="custom-route"
    )
    undeclared_enum_profile = RouterProfile(model=undeclared, provider="custom-route")
    for spec in (
        undeclared,
        undeclared.value,
        undeclared_str_profile,
        undeclared_enum_profile,
    ):
        with pytest.raises(ConfigurationError, match=r"Unknown model"):
            expand_route_plan(spec, config=config)

    with pytest.raises(ConfigurationError, match=r"^Unknown model: no-such-model$"):
        expand_route_plan("no-such-model", config=config)

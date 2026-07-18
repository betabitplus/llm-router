from __future__ import annotations

from dataclasses import replace

import pytest

from llm_router import ConfigurationError, Model, ModelNotFoundError, Provider
from llm_router._api.types import ProviderLimits, RouterProfile
from llm_router._internal.config import build_default_config
from llm_router._internal.runtime.routes import expand_route_plan


def test_model_spec_expands_from_registry_with_default_provider_first() -> None:
    config = build_default_config()

    plan = expand_route_plan(Model.GEMINI_FLASH, config=config)

    assert [route.provider for route in plan.routes] == [
        Provider.AISTUDIO,
        Provider.GOOGLE,
        Provider.GEMINI_WEBAPI,
    ]
    assert [route.route_index for route in plan.routes] == [0, 1, 2]


def test_pinned_profile_resolves_provider_model_and_route_defaults() -> None:
    config = build_default_config()
    profile = RouterProfile(
        model=Model.DEEPSEEK_V3,
        provider="openrouter",
        key_id="auto",
        temperature=0.2,
        seed=12,
        kwargs={"response_format": "json"},
    )

    plan = expand_route_plan(profile, config=config)

    assert len(plan.routes) == 1
    route = plan.routes[0]
    assert route.provider is Provider.OPENROUTER
    assert route.provider_model == "deepseek/deepseek-chat-v3-0324:free"
    assert route.defaults.key_id == "auto"
    assert route.defaults.temperature == 0.2
    assert route.defaults.seed == 12
    assert route.defaults.kwargs == {"response_format": "json"}


def test_sequence_preserves_route_order_and_policy_defaults() -> None:
    config = build_default_config()
    limits = ProviderLimits(
        rps=1.0,
        rpm=60.0,
        cooldown_seconds=0.0,
        cooldown_after_failures=0,
    )

    plan = expand_route_plan(
        [
            RouterProfile(
                model=Model.DEEPSEEK_V3,
                provider=Provider.OPENROUTER,
                max_attempts=2,
                default_limits=limits,
            ),
            RouterProfile(model=Model.LLAMA_SCOUT, provider=Provider.GROQ),
        ],
        config=config,
    )

    assert [route.provider for route in plan.routes] == [
        Provider.OPENROUTER,
        Provider.GROQ,
    ]
    assert plan.policy_defaults == {
        "max_attempts": 2,
        "default_limits": limits,
    }


def test_sequence_indexes_keep_increasing_across_expanded_profiles() -> None:
    config = build_default_config()

    plan = expand_route_plan(
        [
            RouterProfile(model=Model.GEMINI_FLASH),
            RouterProfile(model=Model.DEEPSEEK_V3, provider=Provider.OPENROUTER),
        ],
        config=config,
    )

    assert [route.route_index for route in plan.routes] == [0, 1, 2, 3]
    assert [route.provider for route in plan.routes] == [
        Provider.AISTUDIO,
        Provider.GOOGLE,
        Provider.GEMINI_WEBAPI,
        Provider.OPENROUTER,
    ]


def test_route_plan_copies_mutable_defaults() -> None:
    config = build_default_config()
    route_kwargs = {"response_format": "json"}
    limits = ProviderLimits(
        rps=1.0,
        rpm=60.0,
        cooldown_seconds=0.0,
        cooldown_after_failures=0,
    )
    limits_by_provider = {Provider.OPENROUTER: limits}

    plan = expand_route_plan(
        RouterProfile(
            model=Model.DEEPSEEK_V3,
            provider=Provider.OPENROUTER,
            kwargs=route_kwargs,
            limits_by_provider=limits_by_provider,
        ),
        config=config,
    )
    route_kwargs["response_format"] = "text"
    limits_by_provider.clear()

    assert plan.routes[0].defaults.kwargs == {"response_format": "json"}
    assert plan.policy_defaults["limits_by_provider"] == {
        Provider.OPENROUTER: limits,
    }


def test_conflicting_route_policy_defaults_fail() -> None:
    config = build_default_config()

    with pytest.raises(ConfigurationError, match="Conflicting route policy default"):
        expand_route_plan(
            [
                RouterProfile(model=Model.DEEPSEEK_V3, max_attempts=1),
                RouterProfile(model=Model.LLAMA_SCOUT, max_attempts=2),
            ],
            config=config,
        )


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        ("max_attempts", 0, "max attempts"),
        ("attempt_timeout_seconds", 0.0, "attempt timeout"),
    ],
)
def test_invalid_route_policy_defaults_fail(
    field_name: str,
    value: object,
    message: str,
) -> None:
    config = build_default_config()

    with pytest.raises(ConfigurationError, match=message):
        expand_route_plan(
            RouterProfile(model=Model.DEEPSEEK_V3, **{field_name: value}),
            config=config,
        )


def test_unknown_model_string_fails_as_configuration_error() -> None:
    config = build_default_config()

    with pytest.raises(ConfigurationError, match="Unknown model"):
        expand_route_plan(
            RouterProfile(
                model="definitely-not-a-model",
                provider=Provider.OPENROUTER,
            ),
            config=config,
        )


def test_model_removed_from_config_fails_even_with_unknown_provider() -> None:
    config = build_default_config()
    models = dict(config.models)
    models.pop(Model.DEEPSEEK_V4_FLASH)
    custom_config = replace(config, catalog=replace(config.catalog, models=models))

    with pytest.raises(ConfigurationError, match="Unknown model"):
        expand_route_plan(
            RouterProfile(model=Model.DEEPSEEK_V4_FLASH, provider="not-a-provider"),
            config=custom_config,
        )


def test_valid_provider_without_model_mapping_fails() -> None:
    config = build_default_config()

    with pytest.raises(ModelNotFoundError):
        expand_route_plan(
            RouterProfile(
                model=Model.DEEPSEEK_V3,
                provider=Provider.GOOGLE,
            ),
            config=config,
        )


def test_unknown_provider_string_remains_a_fallback_candidate() -> None:
    config = build_default_config()

    plan = expand_route_plan(
        RouterProfile(
            model=Model.DEEPSEEK_V4_FLASH,
            provider="not-a-provider",
        ),
        config=config,
    )

    assert len(plan.routes) == 1
    assert plan.routes[0].provider == "not-a-provider"
    assert plan.routes[0].provider_model == Model.DEEPSEEK_V4_FLASH.value

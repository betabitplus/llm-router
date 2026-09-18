from __future__ import annotations

from dataclasses import replace

import pytest

from llm_router import ConfigurationError, Provider
from llm_router._internal.config import build_default_config, validate_config
from llm_router._internal.runtime.routes import _resolve_model

pytestmark = [pytest.mark.verification_kind("unit")]


@pytest.mark.verifies("TREQ_CONFIG_RETRY_ATTEMPTS[revision==1]")
@pytest.mark.coverage_item("VC_CONFIG_RETRY_ATTEMPTS")
def test_validation_rejects_invalid_retry_policy() -> None:
    config = build_default_config()
    invalid_retry = replace(config.retry_policy, max_attempts=0)
    invalid_defaults = replace(config.defaults, retry_policy=invalid_retry)
    invalid_config = replace(config, defaults=invalid_defaults)

    with pytest.raises(ConfigurationError, match="retry max attempts"):
        validate_config(invalid_config)


@pytest.mark.verifies("TREQ_CONFIG_ATTEMPT_TIMEOUT[revision==1]")
@pytest.mark.coverage_item("VC_CONFIG_ATTEMPT_TIMEOUT")
def test_validation_rejects_invalid_policy_timeout() -> None:
    config = build_default_config()
    invalid_policy = replace(config.policy, attempt_timeout_seconds=0)
    invalid_defaults = replace(config.defaults, policy=invalid_policy)
    invalid_config = replace(config, defaults=invalid_defaults)

    with pytest.raises(ConfigurationError, match="attempt timeout"):
        validate_config(invalid_config)


@pytest.mark.verifies("TREQ_CONFIG_PROVIDER_IDENTITY[revision==1]")
@pytest.mark.coverage_item("VC_CONFIG_PROVIDER_IDENTITY")
def test_validation_rejects_provider_spec_key_mismatch() -> None:
    config = build_default_config()
    provider_specs = dict(config.catalog.providers)
    provider_specs[Provider.AISTUDIO] = replace(
        provider_specs[Provider.AISTUDIO],
        provider=Provider.GOOGLE,
    )
    invalid_catalog = replace(config.catalog, providers=provider_specs)
    invalid_config = replace(config, catalog=invalid_catalog)

    with pytest.raises(ConfigurationError, match="provider spec key"):
        validate_config(invalid_config)


@pytest.mark.verifies("TREQ_CONFIG_REQUIRED_BASE_URL[revision==1]")
@pytest.mark.coverage_item("VC_CONFIG_REQUIRED_BASE_URL")
def test_validation_rejects_missing_required_base_url() -> None:
    config = build_default_config()
    provider_base_urls = dict(config.provider_base_urls)
    provider_base_urls.pop(Provider.AISTUDIO)
    invalid_catalog = replace(config.catalog, provider_base_urls=provider_base_urls)
    invalid_config = replace(config, catalog=invalid_catalog)

    with pytest.raises(ConfigurationError, match="requires a base URL"):
        validate_config(invalid_config)


@pytest.mark.verifies("TREQ_CONFIG_MODEL_DECLARATION[revision==1]")
@pytest.mark.coverage_item("VC_CONFIG_MODEL_DECLARATION")
def test_requested_model_must_exist_in_effective_registry() -> None:
    config = build_default_config()
    models = dict(config.models)
    models.pop(config.default_model)
    invalid_config = replace(config, catalog=replace(config.catalog, models=models))

    with pytest.raises(ConfigurationError, match="Unknown model"):
        _resolve_model(config.default_model, config=invalid_config)


@pytest.mark.verifies("TREQ_CONFIG_RETRY_WAIT_BOUNDS[revision==1]")
@pytest.mark.coverage_item("VC_CONFIG_RETRY_WAIT_BOUNDS")
@pytest.mark.parametrize(
    ("min_wait_seconds", "max_wait_seconds", "message"),
    [
        (0.0, 1.0, "retry min wait"),
        (2.0, 1.0, "retry max wait"),
    ],
)
def test_validation_rejects_invalid_retry_wait_bounds(
    min_wait_seconds: float,
    max_wait_seconds: float,
    message: str,
) -> None:
    config = build_default_config()
    retry = replace(
        config.retry_policy,
        min_wait_seconds=min_wait_seconds,
        max_wait_seconds=max_wait_seconds,
    )
    invalid_config = replace(
        config, defaults=replace(config.defaults, retry_policy=retry)
    )

    with pytest.raises(ConfigurationError, match=message):
        validate_config(invalid_config)


@pytest.mark.verifies("TREQ_CONFIG_ROUTE_ATTEMPT_LIMIT[revision==1]")
@pytest.mark.coverage_item("VC_CONFIG_ROUTE_ATTEMPT_LIMIT")
def test_validation_rejects_zero_route_attempt_limit() -> None:
    config = build_default_config()
    policy = replace(config.policy, max_attempts=0)
    invalid_config = replace(config, defaults=replace(config.defaults, policy=policy))

    with pytest.raises(ConfigurationError, match="policy max attempts"):
        validate_config(invalid_config)


@pytest.mark.verifies("TREQ_CONFIG_FALLBACK_SHUFFLE_MIN_ROUTES[revision==1]")
@pytest.mark.coverage_item("VC_CONFIG_FALLBACK_SHUFFLE_MIN_ROUTES")
def test_validation_rejects_zero_fallback_shuffle_minimum() -> None:
    config = build_default_config()
    policy = replace(config.policy, min_routes_for_fallback_shuffle=0)
    invalid_config = replace(config, defaults=replace(config.defaults, policy=policy))

    with pytest.raises(ConfigurationError, match="minimum routes"):
        validate_config(invalid_config)


@pytest.mark.verifies("TREQ_CONFIG_TOOL_ROUND_LIMIT[revision==1]")
@pytest.mark.coverage_item("VC_CONFIG_TOOL_ROUND_LIMIT")
def test_validation_rejects_zero_default_tool_rounds() -> None:
    config = build_default_config()
    defaults = replace(config.defaults, default_max_tool_rounds=0)

    with pytest.raises(ConfigurationError, match="default max tool rounds"):
        validate_config(replace(config, defaults=defaults))


@pytest.mark.verifies("TREQ_CONFIG_STRUCTURED_OUTPUT_ATTEMPTS[revision==1]")
@pytest.mark.coverage_item("VC_CONFIG_STRUCTURED_OUTPUT_ATTEMPTS")
def test_validation_rejects_zero_structured_output_attempts() -> None:
    config = build_default_config()
    defaults = replace(config.defaults, structured_output_max_attempts=0)

    with pytest.raises(ConfigurationError, match="structured output max attempts"):
        validate_config(replace(config, defaults=defaults))


@pytest.mark.verifies("TREQ_CONFIG_DEFAULT_PROVIDER_DECLARATION[revision==1]")
@pytest.mark.coverage_item("VC_CONFIG_DEFAULT_PROVIDER_DECLARATION")
def test_validation_rejects_undeclared_default_provider() -> None:
    config = build_default_config()
    providers = dict(config.catalog.providers)
    providers.pop(config.default_provider)
    invalid_config = replace(
        config,
        catalog=replace(config.catalog, providers=providers),
    )

    with pytest.raises(ConfigurationError, match="default provider"):
        validate_config(invalid_config)


@pytest.mark.verifies("TREQ_CONFIG_DEFAULT_MODEL_MAPPING[revision==1]")
@pytest.mark.coverage_item("VC_CONFIG_DEFAULT_MODEL_MAPPING")
def test_validation_rejects_undeclared_default_model() -> None:
    config = build_default_config()
    models = dict(config.models)
    models.pop(config.default_model)
    invalid_config = replace(config, catalog=replace(config.catalog, models=models))

    with pytest.raises(ConfigurationError, match="default model must be present"):
        validate_config(invalid_config)


@pytest.mark.verifies("TREQ_CONFIG_DEFAULT_MODEL_MAPPING[revision==1]")
@pytest.mark.coverage_item("VC_CONFIG_DEFAULT_MODEL_MAPPING")
def test_validation_rejects_default_model_without_default_provider_mapping() -> None:
    config = build_default_config()
    replacement_provider = next(
        provider
        for provider in config.catalog.providers
        if provider != config.default_provider
    )
    models = {model: dict(mappings) for model, mappings in config.models.items()}
    models[config.default_model] = {replacement_provider: "replacement-model"}
    invalid_config = replace(config, catalog=replace(config.catalog, models=models))

    with pytest.raises(ConfigurationError, match="default model must have a mapping"):
        validate_config(invalid_config)


@pytest.mark.verifies("TREQ_CONFIG_MODEL_PROVIDER_REFERENCES[revision==1]")
@pytest.mark.coverage_item("VC_CONFIG_MODEL_PROVIDER_REFERENCES")
def test_validation_rejects_model_without_provider_mapping() -> None:
    config = build_default_config()
    model = next(model for model in config.models if model != config.default_model)
    models = {item: dict(mappings) for item, mappings in config.models.items()}
    models[model] = {}
    invalid_config = replace(config, catalog=replace(config.catalog, models=models))

    with pytest.raises(ConfigurationError, match="must map to a provider"):
        validate_config(invalid_config)


@pytest.mark.verifies("TREQ_CONFIG_MODEL_PROVIDER_REFERENCES[revision==1]")
@pytest.mark.coverage_item("VC_CONFIG_MODEL_PROVIDER_REFERENCES")
def test_validation_rejects_model_mapping_to_undeclared_provider() -> None:
    config = build_default_config()
    candidates = [
        (model, provider)
        for model, mappings in config.models.items()
        for provider in mappings
        if provider != config.default_provider
    ]
    _, provider = candidates[0]
    providers = dict(config.catalog.providers)
    providers.pop(provider)
    invalid_config = replace(
        config,
        catalog=replace(config.catalog, providers=providers),
    )

    with pytest.raises(ConfigurationError, match="references an unknown provider"):
        validate_config(invalid_config)

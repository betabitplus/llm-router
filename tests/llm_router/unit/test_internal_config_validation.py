from __future__ import annotations

from dataclasses import replace

import pytest

from llm_router import ConfigurationError, Provider
from llm_router._internal.config import build_default_config, validate_config


def test_validation_rejects_invalid_retry_policy() -> None:
    config = build_default_config()
    invalid_retry = replace(config.retry_policy, max_attempts=0)
    invalid_defaults = replace(config.defaults, retry_policy=invalid_retry)
    invalid_config = replace(config, defaults=invalid_defaults)

    with pytest.raises(ConfigurationError, match="retry max attempts"):
        validate_config(invalid_config)


def test_validation_rejects_invalid_policy_timeout() -> None:
    config = build_default_config()
    invalid_policy = replace(config.policy, attempt_timeout_seconds=0)
    invalid_defaults = replace(config.defaults, policy=invalid_policy)
    invalid_config = replace(config, defaults=invalid_defaults)

    with pytest.raises(ConfigurationError, match="attempt timeout"):
        validate_config(invalid_config)


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


def test_validation_rejects_missing_required_base_url() -> None:
    config = build_default_config()
    provider_base_urls = dict(config.provider_base_urls)
    provider_base_urls.pop(Provider.AISTUDIO)
    invalid_catalog = replace(config.catalog, provider_base_urls=provider_base_urls)
    invalid_config = replace(config, catalog=invalid_catalog)

    with pytest.raises(ConfigurationError, match="requires a base URL"):
        validate_config(invalid_config)

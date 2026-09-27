# mutation-pin: REQ_REQUEST_OVERRIDE_PRECEDENCE 39cd06b3a9c8bc51
# pinned-by: claude-opus-5-5: The mutant skips applying route policy defaults. A route-level max_attempts=5 is silently dropped and falls back to the config value 3, even though no request override touched it. That breaks the criterion that request overrides take precedence over router and route defaults while unrelated defaults
from __future__ import annotations

import pytest

from llm_router._internal.config import build_default_config
from llm_router._internal.runtime.effective_settings import (
    RouterDefaults,
    resolve_effective_settings,
)
from llm_router._internal.runtime.routes import RouteGenerationDefaults

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_REQUEST_OVERRIDE_PRECEDENCE[revision==1]")
def test_route_policy_defaults_override_config_and_persist_with_unrelated_call_override() -> None:
    config = build_default_config()

    settings_no_override = resolve_effective_settings(
        config=config,
        route_defaults=RouteGenerationDefaults(key_id=0),
        route_policy_defaults={"max_attempts": 5},
        router_defaults=RouterDefaults(),
        call_overrides={},
    )
    assert settings_no_override.max_attempts == 5

    settings_with_unrelated_override = resolve_effective_settings(
        config=config,
        route_defaults=RouteGenerationDefaults(key_id=0),
        route_policy_defaults={"max_attempts": 5},
        router_defaults=RouterDefaults(),
        call_overrides={"temperature": 0.7},
    )
    assert settings_with_unrelated_override.max_attempts == 5
    assert settings_with_unrelated_override.temperature == 0.7

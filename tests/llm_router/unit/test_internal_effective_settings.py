from __future__ import annotations

import pytest

from llm_router import ConfigurationError, Provider, ProviderLimits
from llm_router._internal.config import build_default_config
from llm_router._internal.runtime.effective_settings import (
    resolve_effective_settings,
    split_router_defaults,
)
from llm_router._internal.runtime.routes import RouteGenerationDefaults


def test_effective_settings_resolve_layered_precedence_and_none_clearing() -> None:
    config = build_default_config()
    route_defaults = RouteGenerationDefaults(
        key_id=2,
        temperature=0.2,
        seed=11,
        response_schema={"route": True},
        tools=("route-tool",),
        tool_choice="auto",
        max_tool_rounds=2,
        kwargs={"shared": "route", "route_only": True},
    )
    router_defaults = split_router_defaults(
        {
            "key_id": 3,
            "temperature": 0.6,
            "seed": 22,
            "response_schema": {"router": True},
            "tools": ("router-tool",),
            "tool_choice": "required",
            "max_tool_rounds": 3,
            "shared": "router",
            "router_only": True,
        }
    )

    settings = resolve_effective_settings(
        config=config,
        route_defaults=route_defaults,
        route_policy_defaults={"max_attempts": 4},
        router_defaults=router_defaults,
        call_overrides={
            "temperature": 0.9,
            "response_schema": None,
            "tools": None,
            "shared": "call",
            "call_only": True,
            "key_id": 9,
        },
    )

    assert settings.key_id == 3
    assert settings.temperature == 0.9
    assert settings.seed == 22
    assert settings.response_schema is None
    assert settings.tools is None
    assert settings.tool_choice == "required"
    assert settings.max_tool_rounds == 3
    assert settings.max_attempts == 4
    assert settings.kwargs == {
        "shared": "call",
        "route_only": True,
        "router_only": True,
        "call_only": True,
        "key_id": 9,
    }


def test_policy_defaults_precede_router_defaults() -> None:
    config = build_default_config()
    route_limits = ProviderLimits(
        rps=2.0,
        rpm=30.0,
        cooldown_seconds=10.0,
        cooldown_after_failures=1,
    )
    router_limits = ProviderLimits(
        rps=4.0,
        rpm=60.0,
        cooldown_seconds=20.0,
        cooldown_after_failures=2,
    )

    settings = resolve_effective_settings(
        config=config,
        route_defaults=RouteGenerationDefaults(key_id=1),
        route_policy_defaults={
            "max_attempts": 3,
            "default_limits": route_limits,
        },
        router_defaults=split_router_defaults(
            {
                "max_attempts": 2,
                "default_limits": router_limits,
                "limits_by_provider": {Provider.NVIDIA: router_limits},
            }
        ),
        call_overrides={},
    )

    assert settings.max_attempts == 2
    assert settings.default_limits == router_limits
    assert settings.limits_by_provider == {Provider.NVIDIA: router_limits}


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        ("max_attempts", 0, "max attempts"),
        ("attempt_timeout_seconds", 0.0, "attempt timeout"),
    ],
)
def test_invalid_router_policy_defaults_fail_at_construction(
    field_name: str,
    value: object,
    message: str,
) -> None:
    with pytest.raises(ConfigurationError, match=message):
        split_router_defaults({field_name: value})

from __future__ import annotations

from hypothesis import given, strategies as st

from llm_router._internal.config import build_default_config
from llm_router._internal.runtime.effective_settings import (
    resolve_effective_settings,
    split_router_defaults,
)
from llm_router._internal.runtime.routes import RouteGenerationDefaults

_OPTIONAL_TEMPERATURE = st.one_of(
    st.none(),
    st.floats(
        min_value=0.0,
        max_value=2.0,
        allow_nan=False,
        allow_infinity=False,
    ),
)
_OPTIONAL_ATTEMPTS = st.one_of(st.none(), st.integers(min_value=1, max_value=5))


@given(
    route_temperature=_OPTIONAL_TEMPERATURE,
    router_temperature=_OPTIONAL_TEMPERATURE,
    call_temperature=_OPTIONAL_TEMPERATURE,
    call_is_set=st.booleans(),
)
def test_generation_precedence_preserves_omission_vs_explicit_none(
    *,
    route_temperature: float | None,
    router_temperature: float | None,
    call_temperature: float | None,
    call_is_set: bool,
) -> None:
    config = build_default_config()
    router_defaults = split_router_defaults(
        {} if router_temperature is None else {"temperature": router_temperature}
    )
    call_overrides = {"temperature": call_temperature} if call_is_set else {}

    settings = resolve_effective_settings(
        config=config,
        route_defaults=RouteGenerationDefaults(
            key_id=1,
            temperature=route_temperature,
        ),
        route_policy_defaults={},
        router_defaults=router_defaults,
        call_overrides=call_overrides,
    )

    expected = (
        call_temperature
        if call_is_set
        else router_temperature
        if router_temperature is not None
        else route_temperature
    )
    assert settings.temperature == expected


@given(
    route_schema_is_set=st.booleans(),
    router_schema_is_set=st.booleans(),
    call_clears_schema=st.booleans(),
)
def test_explicit_none_clears_structured_schema_defaults(
    *,
    route_schema_is_set: bool,
    router_schema_is_set: bool,
    call_clears_schema: bool,
) -> None:
    config = build_default_config()
    route_schema = {"layer": "route"} if route_schema_is_set else None
    router_schema = {"layer": "router"} if router_schema_is_set else None

    settings = resolve_effective_settings(
        config=config,
        route_defaults=RouteGenerationDefaults(
            key_id=1,
            response_schema=route_schema,
        ),
        route_policy_defaults={},
        router_defaults=split_router_defaults(
            {} if router_schema is None else {"response_schema": router_schema}
        ),
        call_overrides={"response_schema": None} if call_clears_schema else {},
    )

    expected = (
        None
        if call_clears_schema
        else router_schema
        if router_schema is not None
        else route_schema
    )
    assert settings.response_schema == expected


@given(
    route_attempts=_OPTIONAL_ATTEMPTS,
    router_attempts=_OPTIONAL_ATTEMPTS,
)
def test_policy_precedence_uses_router_defaults_after_route_defaults(
    *,
    route_attempts: int | None,
    router_attempts: int | None,
) -> None:
    config = build_default_config()
    route_policy_defaults = (
        {} if route_attempts is None else {"max_attempts": route_attempts}
    )
    router_defaults = split_router_defaults(
        {} if router_attempts is None else {"max_attempts": router_attempts}
    )

    settings = resolve_effective_settings(
        config=config,
        route_defaults=RouteGenerationDefaults(key_id=1),
        route_policy_defaults=route_policy_defaults,
        router_defaults=router_defaults,
        call_overrides={},
    )

    expected = (
        router_attempts
        if router_attempts is not None
        else route_attempts
        if route_attempts is not None
        else config.policy.max_attempts
    )
    assert settings.max_attempts == expected

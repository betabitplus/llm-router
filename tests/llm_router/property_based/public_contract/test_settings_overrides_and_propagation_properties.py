"""Property-based tests for settings override and propagation invariants.

Why:
    Protects the public settings helpers and active-config snapshot semantics
    through many generated combinations of explicit and omitted values.

How:
    Exercises only the supported public config facade so override behavior stays
    stable even if private config assembly changes.
"""

from __future__ import annotations

from dataclasses import replace

import pytest
from hypothesis import given, settings, strategies as st

from llm_router import RouterConfig, get_config, install_config

# =============================================================================
# Strategies
# =============================================================================


_SAFE_TEXT = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789_-",
    min_size=1,
    max_size=12,
)
_SCALAR = st.one_of(
    st.text(max_size=20),
    st.integers(min_value=-5, max_value=5),
    st.booleans(),
)
_SMALL_MAPPING = st.dictionaries(
    keys=_SAFE_TEXT,
    values=_SCALAR,
    max_size=3,
)
_SCHEMA_MAPPING = st.fixed_dictionaries(
    {
        "type": st.just("object"),
        "title": _SAFE_TEXT,
    }
)
_TOOL_MAPPING = st.fixed_dictionaries({"name": _SAFE_TEXT})
_OPTIONAL_TEMPERATURE = st.one_of(
    st.none(),
    st.floats(
        min_value=-2.0,
        max_value=2.0,
        allow_nan=False,
        allow_infinity=False,
    ),
)
_OPTIONAL_SEED = st.one_of(st.none(), st.integers(min_value=0, max_value=100))
_OPTIONAL_MAX_TOOL_ROUNDS = st.one_of(
    st.none(),
    st.integers(min_value=1, max_value=5),
)
_OPTIONAL_SCHEMA = st.one_of(st.none(), _SCHEMA_MAPPING)
_OPTIONAL_TOOLS = st.one_of(st.none(), st.lists(_TOOL_MAPPING, max_size=2))
_OPTIONAL_TOOL_CHOICE = st.one_of(st.none(), _SAFE_TEXT, _TOOL_MAPPING)


# =============================================================================
# Assertions
# =============================================================================


def assert_router_config_kwargs(
    result: dict[str, object],
    *,
    temperature: float | None,
    seed: int | None,
    response_schema: dict[str, object] | None,
    tools: list[dict[str, str]] | None,
    tool_choice: str | dict[str, object] | None,
    max_tool_rounds: int | None,
    kwargs: dict[str, object],
) -> None:
    """Assert the public omission and preservation contract for config bundles."""
    assert ("temperature" in result) is (temperature is not None)
    assert ("seed" in result) is (seed is not None)
    assert ("response_schema" in result) is (response_schema is not None)
    assert ("tools" in result) is (tools is not None)
    assert ("tool_choice" in result) is (tool_choice is not None)
    assert ("max_tool_rounds" in result) is (max_tool_rounds is not None)
    assert ("kwargs" in result) is bool(kwargs)

    if temperature is not None:
        assert result["temperature"] == temperature
    if seed is not None:
        assert result["seed"] == seed
    if response_schema is not None:
        assert result["response_schema"] == response_schema
    if tools is not None:
        assert result["tools"] == tools
    if tool_choice is not None:
        assert result["tool_choice"] == tool_choice
    if max_tool_rounds is not None:
        assert result["max_tool_rounds"] == max_tool_rounds
    if kwargs:
        assert result["kwargs"] == kwargs
        assert result["kwargs"] is not kwargs


# =============================================================================
# Properties
# =============================================================================


@given(
    temperature=_OPTIONAL_TEMPERATURE,
    seed=_OPTIONAL_SEED,
    response_schema=_OPTIONAL_SCHEMA,
    tools=_OPTIONAL_TOOLS,
    tool_choice=_OPTIONAL_TOOL_CHOICE,
    max_tool_rounds=_OPTIONAL_MAX_TOOL_ROUNDS,
    kwargs=_SMALL_MAPPING,
)
@settings(max_examples=40)
def test_router_config_as_kwargs_keeps_only_explicit_values(
    *,
    temperature: float | None,
    seed: int | None,
    response_schema: dict[str, object] | None,
    tools: list[dict[str, str]] | None,
    tool_choice: str | dict[str, object] | None,
    max_tool_rounds: int | None,
    kwargs: dict[str, object],
) -> None:
    """`RouterConfig.as_kwargs()` should omit `None` and preserve explicit values."""
    # This mirrors the main public precedence rule: omitted values should stay
    # omitted so they can inherit later, while explicit values should survive
    # the expansion into constructor kwargs unchanged.
    config = RouterConfig(
        temperature=temperature,
        seed=seed,
        response_schema=response_schema,
        tools=tools,
        tool_choice=tool_choice,
        max_tool_rounds=max_tool_rounds,
        kwargs=kwargs,
    )

    result = config.as_kwargs()

    # These membership checks are the core property. The helper should expose
    # only the caller's explicit intent, not a dense dict full of implicit
    # `None` values that would accidentally override other layers.
    assert_router_config_kwargs(
        result,
        temperature=temperature,
        seed=seed,
        response_schema=response_schema,
        tools=tools,
        tool_choice=tool_choice,
        max_tool_rounds=max_tool_rounds,
        kwargs=kwargs,
    )


@given(
    default_max_tool_rounds=st.integers(min_value=1, max_value=8),
    structured_output_max_attempts=st.integers(min_value=1, max_value=6),
    retry_max_attempts=st.integers(min_value=1, max_value=5),
    round_robin_start=st.booleans(),
)
@settings(max_examples=20)
def test_install_config_replaces_the_active_public_snapshot(
    *,
    default_max_tool_rounds: int,
    structured_output_max_attempts: int,
    retry_max_attempts: int,
    round_robin_start: bool,
) -> None:
    """`install_config()` and `get_config()` should expose one active snapshot."""
    # This property protects the public runtime-config lifecycle, not the
    # internals of config assembly. Installing a new snapshot should atomically
    # replace what later public readers observe.
    original = get_config()
    updated_defaults = replace(
        original.defaults,
        default_max_tool_rounds=default_max_tool_rounds,
        structured_output_max_attempts=structured_output_max_attempts,
        retry_policy=replace(
            original.retry_policy,
            max_attempts=retry_max_attempts,
        ),
        policy=replace(
            original.policy,
            round_robin_start=round_robin_start,
        ),
    )
    updated = replace(original, defaults=updated_defaults)

    try:
        installed = install_config(updated)
        current = get_config()

        assert installed is updated
        assert current is updated
        assert current.default_max_tool_rounds == default_max_tool_rounds
        assert current.structured_output_max_attempts == structured_output_max_attempts
        assert current.retry_policy.max_attempts == retry_max_attempts
        assert current.policy.round_robin_start is round_robin_start
    finally:
        install_config(original)


# =============================================================================
# Tests
# =============================================================================


def test_install_config_rejects_non_config_objects() -> None:
    """Only the public `LLMRouterConfig` snapshot type should be installable."""
    with pytest.raises(TypeError, match="LLMRouterConfig instance"):
        install_config(object())  # type: ignore[arg-type]

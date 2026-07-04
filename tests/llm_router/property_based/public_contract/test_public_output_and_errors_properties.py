"""Property-based tests for public output boundary invariants.

Why:
    Protects the normalized response wrapper so explicit public output meaning
    stays stable across many generated payload shapes.

How:
    Exercises only the supported public response model and its default-field
    behavior.
"""

from __future__ import annotations

from hypothesis import given, strategies as st

from llm_router import (
    LLMRouterResponse,
    RoutingAttempt,
    ToolCall,
    ToolStep,
    UsageStats,
)

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
_USAGE = st.builds(
    UsageStats,
    input_tokens=st.integers(min_value=0, max_value=500),
    output_tokens=st.integers(min_value=0, max_value=500),
    total_tokens=st.integers(min_value=0, max_value=1000),
)
_TOOL_CALL = st.builds(
    ToolCall,
    id=st.one_of(st.none(), _SAFE_TEXT),
    name=_SAFE_TEXT,
    args=_SMALL_MAPPING,
    raw_arguments=st.one_of(st.none(), _SAFE_TEXT),
)
_TOOL_STEP = st.builds(
    ToolStep,
    tool_name=_SAFE_TEXT,
    args=_SMALL_MAPPING,
    result=_SCALAR,
    call_id=st.one_of(st.none(), _SAFE_TEXT),
)
_ROUTING_ATTEMPT = st.builds(
    RoutingAttempt,
    profile_name=st.one_of(st.none(), _SAFE_TEXT),
    route_index=st.integers(min_value=0, max_value=5),
    provider=_SAFE_TEXT,
    model=_SAFE_TEXT,
    key_id=st.integers(min_value=0, max_value=5),
    wait_seconds=st.floats(
        min_value=0.0,
        max_value=10.0,
        allow_nan=False,
        allow_infinity=False,
    ),
    temperature=_OPTIONAL_TEMPERATURE,
    seed=_OPTIONAL_SEED,
    max_tool_rounds=st.integers(min_value=1, max_value=5),
    error_type=st.one_of(st.none(), _SAFE_TEXT),
    error_message=st.one_of(st.none(), _SAFE_TEXT),
)


# =============================================================================
# Assertions
# =============================================================================


def assert_response_fields(
    response: LLMRouterResponse,
    *,
    provider: str,
    model: str,
    output_text: str,
    usage: UsageStats | None,
    tool_calls: list[ToolCall],
    tool_trace: list[ToolStep],
    routing_trace: list[RoutingAttempt],
) -> None:
    """Assert the normalized public response wrapper fields."""
    assert response.provider == provider
    assert response.model == model
    assert response.output_text == output_text
    assert response.usage == usage
    assert response.tool_calls == tool_calls
    assert response.tool_trace == tool_trace
    assert response.routing_trace == routing_trace


# =============================================================================
# Properties
# =============================================================================


@given(
    provider=_SAFE_TEXT,
    model=_SAFE_TEXT,
    output_text=st.text(max_size=40),
    usage=st.one_of(st.none(), _USAGE),
    tool_calls=st.lists(_TOOL_CALL, max_size=3),
    tool_trace=st.lists(_TOOL_STEP, max_size=3),
    routing_trace=st.lists(_ROUTING_ATTEMPT, max_size=3),
)
def test_llm_router_response_preserves_explicit_public_fields(
    *,
    provider: str,
    model: str,
    output_text: str,
    usage: UsageStats | None,
    tool_calls: list[ToolCall],
    tool_trace: list[ToolStep],
    routing_trace: list[RoutingAttempt],
) -> None:
    """`LLMRouterResponse` should preserve the normalized public payload it is given."""
    # This response wrapper is the main normalized success boundary. The core
    # property is simple: once the runtime has normalized the result, the
    # public model should preserve that meaning without surprise rewriting.
    response = LLMRouterResponse(
        data={"ok": True},
        usage=usage,
        provider=provider,
        model=model,
        output_text=output_text,
        tool_calls=tool_calls,
        tool_trace=tool_trace,
        routing_trace=routing_trace,
    )

    assert_response_fields(
        response,
        provider=provider,
        model=model,
        output_text=output_text,
        usage=usage,
        tool_calls=tool_calls,
        tool_trace=tool_trace,
        routing_trace=routing_trace,
    )


# =============================================================================
# Tests
# =============================================================================


def test_llm_router_response_default_lists_are_not_shared() -> None:
    """Default list fields should be isolated across response instances."""
    # This is a small but important public-model guarantee. Trace lists belong
    # to one response, never to some accidentally shared global default.
    first = LLMRouterResponse(data=None, provider="p", model="m")
    second = LLMRouterResponse(data=None, provider="p", model="m")

    first.tool_calls.append(ToolCall(name="tool"))
    first.tool_trace.append(ToolStep(tool_name="tool"))
    first.routing_trace.append(
        RoutingAttempt(
            route_index=0,
            provider="p",
            model="m",
            key_id=0,
            max_tool_rounds=1,
        )
    )

    assert second.tool_calls == []
    assert second.tool_trace == []
    assert second.routing_trace == []

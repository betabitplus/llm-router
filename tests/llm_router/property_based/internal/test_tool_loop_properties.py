from __future__ import annotations

from hypothesis import given, strategies as st

from llm_router._internal.capabilities.tools import (
    ToolLoopState,
    ToolRegistry,
    run_tool_round,
)


def echo(value: int) -> int:
    return value


@given(
    max_rounds=st.integers(min_value=1, max_value=5),
    completed_rounds=st.integers(min_value=0, max_value=6),
    value=st.integers(min_value=0, max_value=100),
)
def test_tool_round_progression_respects_max_rounds(
    *,
    max_rounds: int,
    completed_rounds: int,
    value: int,
) -> None:
    registry = ToolRegistry.from_tools([echo])
    state = ToolLoopState(
        max_rounds=max_rounds,
        completed_rounds=completed_rounds,
    )

    next_state = run_tool_round(
        state=state,
        tool_calls=[{"name": "echo", "args": {"value": value}}],
        registry=registry,
    )

    if completed_rounds < max_rounds:
        assert next_state.completed_rounds == completed_rounds + 1
        assert next_state.outstanding_tool_calls == ()
        assert next_state.steps[-1].result == value
    else:
        assert next_state.completed_rounds == completed_rounds
        assert next_state.steps == ()
        assert len(next_state.outstanding_tool_calls) == 1


def test_tool_loop_state_defaults_are_not_shared() -> None:
    first = ToolLoopState(max_rounds=1)
    second = ToolLoopState(max_rounds=1)
    registry = ToolRegistry.from_tools([echo])

    updated = run_tool_round(
        state=first,
        tool_calls=[{"name": "echo", "args": {"value": 1}}],
        registry=registry,
    )

    assert second.steps == ()
    assert updated.steps != second.steps

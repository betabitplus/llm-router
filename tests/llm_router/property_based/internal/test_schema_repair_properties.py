from __future__ import annotations

from hypothesis import given, strategies as st

from llm_router._internal.capabilities.schema import (
    SchemaRepairState,
    advance_repair_attempt,
    build_repair_prompt,
    normalize_schema,
)


@given(
    max_attempts=st.integers(min_value=1, max_value=8),
    steps=st.integers(min_value=0, max_value=12),
)
def test_repair_attempt_counter_progression_is_monotonic(
    *,
    max_attempts: int,
    steps: int,
) -> None:
    state = SchemaRepairState(max_attempts=max_attempts)

    for _ in range(steps):
        state = advance_repair_attempt(state)

    assert state.completed_attempts == steps
    assert state.can_attempt_repair() is (steps < max_attempts)


@given(
    invalid_output=st.text(min_size=0, max_size=2_000),
    error_message=st.text(min_size=0, max_size=2_000),
)
def test_repair_prompt_uses_bounded_safe_previews(
    *,
    invalid_output: str,
    error_message: str,
) -> None:
    spec = normalize_schema({"title": "Reply", "type": "object"})

    prompt = build_repair_prompt(
        spec=spec,
        invalid_output=invalid_output,
        error_message=error_message,
    )

    assert "Schema: Reply" in prompt
    assert "Return only valid JSON" in prompt
    assert len(prompt) <= 1_200

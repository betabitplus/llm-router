# mutation-pin: TREQ_REPAIR_PROMPT_BOUNDS 65a49b2023696bc9
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import pytest
from hypothesis import given, settings, strategies as st

from llm_router._internal.capabilities.schema import (
    build_repair_prompt,
    normalize_schema,
)

pytestmark = pytest.mark.verification_kind("unit")

_PREFIX = "Schema: "
_NEXT = "\nRequired schema preview: "


def _name_segment(name: str) -> str:
    spec = normalize_schema({"title": name, "type": "object"})
    prompt = build_repair_prompt(
        spec=spec,
        invalid_output="bad",
        error_message="oops",
    )
    assert len(prompt) <= 1_200
    start = prompt.index(_PREFIX) + len(_PREFIX)
    return prompt[start : prompt.index(_NEXT, start)]


@pytest.mark.verifies("TREQ_REPAIR_PROMPT_BOUNDS[revision==2]")
@settings(max_examples=60, deadline=None)
@given(
    name=st.text(
        alphabet=st.characters(blacklist_categories=("Cs",)),
        min_size=121,
        max_size=20_000,
    ),
)
def test_arbitrary_long_schema_name_is_capped_at_120(name: str) -> None:
    assert len(_name_segment(name)) <= 120


@pytest.mark.verifies("TREQ_REPAIR_PROMPT_BOUNDS[revision==2]")
@settings(max_examples=20, deadline=None)
@given(length=st.integers(min_value=100_000, max_value=300_000))
def test_huge_schema_name_is_capped_at_120(length: int) -> None:
    assert len(_name_segment("n" * length)) <= 120


@pytest.mark.verifies("TREQ_REPAIR_PROMPT_BOUNDS[revision==2]")
@settings(max_examples=30, deadline=None)
@given(length=st.integers(min_value=20, max_value=120))
def test_schema_name_within_cap_is_kept_whole(length: int) -> None:
    name = "s" * length
    assert _name_segment(name) == name

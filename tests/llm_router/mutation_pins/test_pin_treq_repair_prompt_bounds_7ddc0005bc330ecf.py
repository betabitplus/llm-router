# mutation-pin: TREQ_REPAIR_PROMPT_BOUNDS 7ddc0005bc330ecf
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import pytest

from llm_router._internal.capabilities.schema import (
    build_repair_prompt,
    normalize_schema,
)

pytestmark = pytest.mark.verification_kind("unit")

_MARKER = "Previous response preview: "
_TAIL = "\nReturn only valid JSON that satisfies the schema."


@pytest.mark.verifies("TREQ_REPAIR_PROMPT_BOUNDS[revision==2]")
def test_repair_prompt_output_preview_is_capped_at_500_chars() -> None:
    spec = normalize_schema({"title": "Person", "type": "object"})
    invalid_output = " ".join(f"word{index}" for index in range(2_000))
    assert len(invalid_output) > 10_000

    prompt = build_repair_prompt(
        spec=spec,
        invalid_output=invalid_output,
        error_message="bad output",
    )

    section = prompt.split(_MARKER, 1)[1]
    assert section.endswith(_TAIL)
    preview = section[: -len(_TAIL)]
    assert len(preview) <= 500
    assert len(preview) >= 450
    assert len(prompt) <= 1_200

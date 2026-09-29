# mutation-pin: TREQ_REPAIR_PROMPT_BOUNDS 3d767806f2945e38
# pinned-by: claude-opus-5-5 and gemini-3.1-pro-high
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import pytest

from llm_router._internal.capabilities.schema import (
    build_repair_prompt,
    normalize_schema,
)

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_REPAIR_PROMPT_BOUNDS[revision==2]")
def test_validation_error_preview_is_capped_at_300_chars() -> None:
    spec = normalize_schema({"title": "Answer", "type": "object"})
    message = " ".join(f"field{index} is missing" for index in range(400))
    assert len(message) > 5_000
    prompt = build_repair_prompt(
        spec=spec,
        invalid_output="ok",
        error_message=message,
    )
    label = "Validation error: "
    error_line = next(line for line in prompt.split("\n") if line.startswith(label))
    assert len(label) + 250 <= len(error_line) <= len(label) + 300

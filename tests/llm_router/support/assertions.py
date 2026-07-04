"""llm_router-specific response and session assertions.

Why:
    Keeps repeated llm_router assertions in one place so e2e scripts stay
    focused on scenario setup and flow.

When to use:
    Import these helpers when a test needs to validate `LLMRouterResponse`
    fields, parsed JSON output, or saved `Session` state.

How:
    Use these assertions from `tests.llm_router.e2e` modules instead of
    repeating response-shape checks inline.

Examples:
    assert_output_text_not_empty(response)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from llm_router import LLMRouterResponse, Session


def assert_response_has_data(response: LLMRouterResponse) -> None:
    """Assert that the provider returned structured response data."""
    assert response.data is not None


def assert_output_text_not_empty(response: LLMRouterResponse) -> None:
    """Assert that the model returned non-empty output text."""
    assert response.output_text.strip()


def assert_session_history_length(
    session_path: Path,
    *,
    expected_length: int,
) -> Session:
    """Load a session and assert the expected number of messages."""
    loaded = Session.load(session_path)
    assert len(loaded.history) == expected_length
    return loaded


def parse_json_object(text: str) -> dict[str, Any]:
    """Parse a JSON object from model output, tolerating code fences."""
    start = min(
        [index for index in (text.find("{"), text.find("[")) if index != -1],
        default=-1,
    )
    end = max(text.rfind("}"), text.rfind("]"))
    json_text = text[start : end + 1] if start != -1 and end != -1 else text
    value = json.loads(json_text)
    if not isinstance(value, dict):
        msg = "Expected a JSON object"
        raise TypeError(msg)
    return value

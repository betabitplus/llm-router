"""LLM Router e2e: session media persistence and assistant metadata.

Why:
    Verifies media persistence and assistant metadata inside saved
    sessions.

Covers:
    Area: AIStudio session flow
    Behavior: video input, `Session.save(...)`, assistant metadata
    persistence
    Interface: `LLMRouter(..., session=...)`, `query(...)`

Checks:
    If the one-turn media request succeeds, then the visible assistant reply is non-
    empty.
    If the saved session is reloaded, then it contains exactly one user turn and one
    assistant turn.
    If media parts are preserved, then the user turn reconstructs a text part plus a
    materialized `VideoSchema` file.
    If assistant text is preserved, then the reloaded assistant parts exactly match the
    original output text.
    If assistant metadata is preserved, then provider and model match the response and
    usage keeps non-negative total tokens.
    If routing metadata is preserved, then the saved trace has one `aistudio` entry at
    route index `0`.

"""

from __future__ import annotations

from pathlib import Path

import pytest

from llm_router import (
    LLMRouter,
    LLMRouterResponse,
    Model,
    Provider,
    RouterProfile,
    Session,
    VideoSchema,
)
from tests.llm_router.support.assertions import assert_output_text_not_empty
from tests.llm_router.support.builders import build_test_video_file

pytestmark = [
    pytest.mark.cap_session,
    pytest.mark.cap_video,
]


# =============================================================================
# Scenario
# =============================================================================

_SYSTEM_PROMPT = "Follow instructions exactly. Reply with only what is asked."


# =============================================================================
# Helpers
# =============================================================================

# No local helpers for this scenario.

# =============================================================================
# Pipeline
# =============================================================================


def build_router(*, session: Session) -> LLMRouter:
    """Build the router under test."""
    return LLMRouter(
        RouterProfile(provider=Provider.AISTUDIO, model=Model.GEMINI_FLASH),
        session=session,
        temperature=0.0,
        seed=42,
    )


def run_pipeline(*, session_path: Path) -> LLMRouterResponse:
    """Run one media turn, then persist the session."""
    session = Session(system=_SYSTEM_PROMPT)
    router = build_router(session=session)
    # One text instruction plus one video file is enough to create both media
    # parts and assistant metadata in the saved session.
    response = router.query(
        [
            "Reply with a short description of the clip.",
            build_test_video_file(),
        ]
    )
    # Save immediately so we can inspect exactly what the session serialized.
    session.save(session_path)
    return response


# =============================================================================
# Assertions
# =============================================================================


def assert_pipeline_response(
    response: LLMRouterResponse,
    *,
    session_path: Path,
) -> None:
    """Assert persisted media parts and assistant metadata."""
    # Start by proving the visible assistant answer was non-empty.
    assert_output_text_not_empty(response)

    loaded = Session.load(session_path)
    # The saved session should contain exactly one user turn and one assistant turn.
    assert len(loaded.history) == 2

    user_message = loaded.history[0]
    # The reloaded user turn must reconstruct both the text instruction and the
    # video attachment as public session parts.
    assert user_message.role == "user"
    assert isinstance(user_message.parts[0], str)
    assert isinstance(user_message.parts[1], VideoSchema)
    assert Path(user_message.parts[1].path).exists()

    assistant_message = loaded.history[1]
    # The assistant turn should replay the original output text exactly.
    assert assistant_message.role == "assistant"
    assert assistant_message.parts == (response.output_text,)

    meta = assistant_message.meta
    # The stored metadata must preserve the execution context needed for resume
    # or debugging: provider, model, usage, and routing trace.
    assert meta["provider"] == response.provider
    assert meta["model"] == response.model
    assert meta["usage"]["total_tokens"] >= 0
    assert len(meta["routing_trace"]) == 1
    assert meta["routing_trace"][0]["provider"] == Provider.AISTUDIO.value
    assert meta["routing_trace"][0]["route_index"] == 0


# =============================================================================
# Tests
# =============================================================================


@pytest.mark.hermetic
@pytest.mark.vcr
def test_pipeline(tmp_path: Path) -> None:
    """Verify media parts and assistant metadata survive session save/load."""
    session_path = tmp_path / "chat_session_media_metadata.json"
    # First run the one-turn media workflow and persist it.
    response = run_pipeline(session_path=session_path)
    # Then inspect the reloaded session for media and metadata preservation.
    assert_pipeline_response(response, session_path=session_path)

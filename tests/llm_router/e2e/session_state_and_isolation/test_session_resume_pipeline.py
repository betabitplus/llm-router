"""LLM Router e2e: session save, load, and resume.

Why:
    Verifies session resume behavior for the Gemini WebAPI provider.

Covers:
    Area: Gemini WebAPI session flow
    Behavior: `Session.save(...)`, `Session.load(...)`, resumed
    conversation
    Interface: `LLMRouter(..., session=...)`, `query(...)`

Checks:
    If the first turn is saved and reloaded successfully, then the resumed response
    output is non-empty.
    If the reloaded session is asked to recall the code, then the resumed reply is
    `81723`.
    If the resumed session is saved again after the second turn, then the persisted
    history length is `4`.

Notes:
    Live execution requires a local browser-cookie setup for Gemini
    WebAPI access.

"""

from pathlib import Path

import pytest

from llm_router import (
    LLMRouter,
    LLMRouterResponse,
    Model,
    Provider,
    RouterProfile,
    Session,
)
from tests.llm_router.support.assertions import (
    assert_output_text_not_empty,
    assert_session_history_length,
)
from tests.llm_router.support.media.gemini_webapi import (
    require_runtime,
)

pytestmark = [
    pytest.mark.cap_session,
]


# =============================================================================
# Scenario
# =============================================================================

_SYSTEM_PROMPT = "Follow instructions exactly. Reply with only what is asked."
_ASK_REMEMBER = "Secret code for this chat: 81723. Reply only OK."
_ASK_RECALL = "What is the secret code? Reply only digits, no punctuation or words."


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
        RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.GEMINI_WEBAPI),
        session=session,
        temperature=0.0,
        seed=42,
    )


def run_pipeline(*, session_path: Path) -> LLMRouterResponse:
    """Run one turn, persist, reload, and resume the session."""
    session = Session(system=_SYSTEM_PROMPT)
    router = build_router(session=session)

    # Turn 1 creates the memory that the resumed session must preserve.
    first_response = router.query(_ASK_REMEMBER)
    assert first_response.data is not None

    # Save and reload before asking the recall question.
    session.save(session_path)
    loaded = Session.load(session_path)
    resumed_router = build_router(session=loaded)

    # Turn 2 is the real proof: can the resumed session still answer correctly?
    response = resumed_router.query(_ASK_RECALL)
    assert response.data is not None

    loaded.save(session_path)
    return response


# =============================================================================
# Assertions
# =============================================================================


def assert_pipeline_response(
    response: LLMRouterResponse,
    *,
    session_path: Path,
) -> None:
    """Assert the resumed-session response and persisted state."""
    # The resumed reply must contain real output before we check its content.
    assert_output_text_not_empty(response)
    # The key contract is that the loaded session still remembers the original code.
    assert response.output_text.strip() == "81723"
    # Four history entries prove both turns were persisted after save-load-resume.
    assert_session_history_length(session_path, expected_length=4)


# =============================================================================
# Tests
# =============================================================================


@pytest.mark.hermetic
@pytest.mark.vcr
def test_pipeline(tmp_path: Path) -> None:
    """Verify session resume works for Gemini WebAPI."""
    require_runtime()

    session_path = tmp_path / "chat_session_resume_gemini_webapi.json"
    # First run the save-load-resume workflow.
    response = run_pipeline(session_path=session_path)
    # Then prove the resumed session still remembers the original turn.
    assert_pipeline_response(response, session_path=session_path)
